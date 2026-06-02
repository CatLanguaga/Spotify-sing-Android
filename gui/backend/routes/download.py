import asyncio
import hashlib
import json
import os
import re
import shutil
import sys
import threading
import time
import uuid
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

_ROOT = Path(os.environ.get("SPOTIFY_SYNC_ROOT", Path(__file__).resolve().parent.parent.parent.parent))
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from gui.backend.models import QueueItem, QueueStatus
from gui.backend.routes import queue as queue_routes
from src.config import ConfigManager
from src.downloader import download_audio, find_ffmpeg
from src.spotify_url import resolve_spotify_url
from src.spotify_client import SpotifyClient
from src.youtube_client import YouTubeClient

router = APIRouter(tags=["download"])

_config = ConfigManager()

# In-memory job store for playlist/album batch jobs
_JOBS: Dict[str, dict] = {}
_JOBS_LOCK = threading.Lock()

# YouTube search cache: spotify_id -> {url, score, candidates, ts}
_YT_CACHE: Dict[str, dict] = {}
_YT_CACHE_LOCK = threading.Lock()
_YT_CACHE_TTL = 3600  # seconds

REVIEW_SCORE_THRESHOLD = 65  # below this, ask user to review (when manual_review_enabled)

# Cap simultaneous YouTube downloads so a 50-track batch doesn't saturate
# network/CPU. The limit is configurable at runtime from config/env.
def _download_limit() -> int:
    cfg = _config.load_config() or {}
    raw = cfg.get("max_concurrent_downloads", os.environ.get("SPOTIFY_MAX_CONCURRENT_DOWNLOADS", 3))
    try:
        return max(1, min(5, int(raw)))
    except (TypeError, ValueError):
        return 3


class _DownloadGate:
    def __init__(self) -> None:
        self._cond = threading.Condition()
        self._active = 0

    def __enter__(self):
        with self._cond:
            while self._active >= _download_limit():
                self._cond.wait(timeout=0.5)
            self._active += 1
        return self

    def __exit__(self, exc_type, exc, tb):
        with self._cond:
            self._active = max(0, self._active - 1)
            self._cond.notify_all()


_DOWNLOAD_GATE = _DownloadGate()

# In-memory store for ZIP batch jobs: job_id -> {state, progress, zip_path, ...}
_BATCH_JOBS: Dict[str, dict] = {}
_BATCH_JOBS_LOCK = threading.Lock()


class DirectDownloadRequest(BaseModel):
    url: str
    fmt: str = "mp3"
    quality: int = 320


class TrackDownloadRequest(BaseModel):
    spotify_id: str
    fmt: str = "mp3"
    quality: int = 320


class ConfirmDownloadRequest(BaseModel):
    item_id: str
    youtube_url: str


class BatchDownloadRequest(BaseModel):
    spotify_ids: List[str]
    fmt: str = "mp3"
    quality: int = 320


class DependencyStatus(BaseModel):
    ffmpeg: bool
    pytubefix: bool
    mutagen: bool
    pillow: bool
    ready: bool


def _detect(url: str) -> Optional[dict]:
    parsed = resolve_spotify_url(url)
    if not parsed:
        return None
    return {"type": parsed["kind"], "id": parsed["id"]}


def _get_spotify_client() -> SpotifyClient:
    cfg = _config.load_config()
    if not cfg or not cfg.get("spotify_client_id"):
        raise HTTPException(400, "Spotify credentials not configured.")
    return SpotifyClient(cfg["spotify_client_id"], cfg["spotify_client_secret"])


def _check_dependencies() -> DependencyStatus:
    ffmpeg_ok = find_ffmpeg() is not None
    try:
        import pytubefix  # noqa: F401
        pytubefix_ok = True
    except Exception:
        pytubefix_ok = False
    try:
        import mutagen  # noqa: F401
        mutagen_ok = True
    except Exception:
        mutagen_ok = False
    try:
        import PIL  # noqa: F401
        pillow_ok = True
    except Exception:
        pillow_ok = False
    return DependencyStatus(
        ffmpeg=ffmpeg_ok,
        pytubefix=pytubefix_ok,
        mutagen=mutagen_ok,
        pillow=pillow_ok,
        ready=ffmpeg_ok and pytubefix_ok and mutagen_ok and pillow_ok,
    )


def _sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _new_job(url: str, kind: str) -> str:
    job_id = str(uuid.uuid4())
    with _JOBS_LOCK:
        _JOBS[job_id] = {
            "id": job_id,
            "url": url,
            "kind": kind,
            "state": "queued",
            "progress": {"done": 0, "total": 0},
            "queue_ids": [],
            "error": None,
            "created_at": datetime.utcnow().isoformat(),
        }
    return job_id


def _update_job(job_id: str, **patch) -> None:
    with _JOBS_LOCK:
        if job_id in _JOBS:
            _JOBS[job_id].update(patch)


def _track_to_queue_item(track: dict, fmt: str, quality: int) -> dict:
    item = QueueItem(
        id=str(uuid.uuid4()),
        title=track.get("name", ""),
        artist=track.get("all_artists") or track.get("artist", ""),
        album=track.get("album", ""),
        language=track.get("language", "Other"),
        score=0.0,
        status=QueueStatus.pending,
        spotify_id=track.get("spotify_id", ""),
        cover_url=track.get("album_art_url"),
        fmt=fmt,
        quality=quality,
        year=str(track.get("year", "")),
        track_number=int(track.get("track_number", 0)),
    )
    return item.model_dump()


def _run_direct_job(job_id: str, url: str, fmt: str, quality: int) -> None:
    deps = _check_dependencies()
    if not deps.ready:
        missing = [k for k, v in deps.model_dump().items() if v is False and k != "ready"]
        _update_job(job_id, state="error", error=f"Missing dependencies: {', '.join(missing)}")
        return

    try:
        parsed = _detect(url)
    except Exception as exc:
        _update_job(job_id, state="error", error=f"Spotify URL lookup failed: {exc}")
        return
    if not parsed:
        _update_job(job_id, state="error", error="Invalid Spotify URL")
        return

    _update_job(job_id, state="resolving")

    try:
        client = _get_spotify_client()
    except HTTPException as exc:
        _update_job(job_id, state="error", error=exc.detail)
        return

    tracks: List[dict] = []
    try:
        if parsed["type"] == "playlist":
            offset = 0
            while True:
                batch = client.get_playlist_tracks(parsed["id"], offset=offset, limit=100)
                if not batch:
                    break
                tracks.extend(batch)
                if len(batch) < 100:
                    break
                offset += 100
        elif parsed["type"] == "track":
            if not client.authenticate():
                _update_job(job_id, state="error", error="Spotify auth failed")
                return
            track = client.sp.track(parsed["id"])
            album = track.get("album", {})
            album_art_url = None
            if album.get("images"):
                album_art_url = album["images"][0]["url"]
            tracks.append({
                "name": track["name"],
                "artist": track["artists"][0]["name"] if track["artists"] else "Unknown",
                "all_artists": ", ".join(a["name"] for a in track["artists"]),
                "album": album.get("name", ""),
                "album_art_url": album_art_url,
                "track_number": track.get("track_number", 1),
                "spotify_id": track.get("id", ""),
                "language": "Other",
            })
        elif parsed["type"] == "album":
            if not client.authenticate():
                _update_job(job_id, state="error", error="Spotify auth failed")
                return
            album = client.sp.album(parsed["id"])
            album_art_url = album["images"][0]["url"] if album.get("images") else None
            for track in album["tracks"]["items"]:
                tracks.append({
                    "name": track["name"],
                    "artist": track["artists"][0]["name"] if track["artists"] else "Unknown",
                    "all_artists": ", ".join(a["name"] for a in track["artists"]),
                    "album": album.get("name", ""),
                    "album_art_url": album_art_url,
                    "track_number": track.get("track_number", 1),
                    "spotify_id": track.get("id", ""),
                    "language": "Other",
                })
    except Exception as exc:
        _update_job(job_id, state="error", error=f"Spotify fetch failed: {exc}")
        return

    if not tracks:
        _update_job(job_id, state="error", error="No tracks resolved from URL")
        return

    items = queue_routes._load()
    queue_ids: List[str] = []
    for track in tracks:
        record = _track_to_queue_item(track, fmt, quality)
        items.append(record)
        queue_ids.append(record["id"])
    queue_routes._save(items)

    _update_job(
        job_id,
        state="done",
        progress={"done": len(queue_ids), "total": len(queue_ids)},
        queue_ids=queue_ids,
    )


@router.get("/download/health", response_model=DependencyStatus)
def download_health():
    """Report whether ffmpeg + pytubefix are available."""
    return _check_dependencies()


@router.post("/download/direct")
def download_direct(payload: DirectDownloadRequest, background_tasks: BackgroundTasks):
    """Accept a Spotify URL, push tracks into the queue, return job_id immediately."""
    deps = _check_dependencies()
    if not deps.ready:
        missing = [k for k, v in deps.model_dump().items() if v is False and k != "ready"]
        raise HTTPException(503, f"Server missing dependencies: {', '.join(missing)}")

    try:
        parsed = _detect(payload.url)
    except Exception as exc:
        raise HTTPException(502, f"Spotify URL lookup failed: {exc}") from exc
    if not parsed:
        raise HTTPException(400, "URL must be a Spotify track, album, or playlist link.")

    job_id = _new_job(payload.url, parsed["type"])
    background_tasks.add_task(_run_direct_job, job_id, payload.url, payload.fmt, payload.quality)
    return {"job_id": job_id, "kind": parsed["type"]}


def _resolve_track(spotify_id: str, fmt: str, quality: int) -> dict:
    """
    Blocking: Spotify lookup + scored YouTube search.
    Returns a data dict with all fields needed to create a QueueItem and start the download.
    """
    client = _get_spotify_client()
    if not client.authenticate():
        raise HTTPException(500, "Spotify auth failed")

    try:
        t = client.sp.track(spotify_id)
    except Exception as exc:
        raise HTTPException(404, f"Spotify track lookup failed: {exc}")

    album = t.get("album", {}) or {}
    art = album.get("images", [{}])[0].get("url") if album.get("images") else None
    name = t["name"]
    artist = t["artists"][0]["name"] if t["artists"] else "Unknown"
    all_artists = ", ".join(a["name"] for a in t["artists"])
    duration_ms = t.get("duration_ms")
    year = (album.get("release_date") or "")[:4]
    track_number = t.get("track_number", 0)

    # Check YT cache first
    now = time.time()
    with _YT_CACHE_LOCK:
        cached = _YT_CACHE.get(spotify_id)
        if cached and (now - cached["ts"]) < _YT_CACHE_TTL:
            youtube_url = cached["url"]
            score = cached["score"]
            candidates = cached["candidates"]
            cached = True
        else:
            cached = False

    if not cached:
        yt = YouTubeClient()
        best, score, candidates = yt.find_best_match(name, artist, duration_ms=duration_ms)
        if not best:
            raise HTTPException(404, "No YouTube match found.")
        youtube_url = best["url"]
        with _YT_CACHE_LOCK:
            _YT_CACHE[spotify_id] = {
                "url": youtube_url, "score": score, "candidates": candidates, "ts": now,
            }

    track_info = {
        "name":          name,
        "artist":        artist,
        "album":         album.get("name", ""),
        "all_artists":   all_artists,
        "album_art_url": art,
        "year":          year,
        "track_number":  track_number,
        "spotify_id":    spotify_id,
        "spotify_url":   f"https://open.spotify.com/track/{spotify_id}",
        "lyrics":        t.get("lyrics") or t.get("lyrics_text") or "",
    }

    return {
        "name":         name,
        "artist":       artist,
        "all_artists":  all_artists,
        "album_name":   album.get("name", ""),
        "art":          art,
        "youtube_url":  youtube_url,
        "score":        score,
        "candidates":   candidates,
        "track_info":   track_info,
        "fmt":          fmt,
        "quality":      quality,
        "year":         year,
        "track_number": track_number,
        "spotify_id":   spotify_id,
    }


def _make_queue_item(data: dict, status: QueueStatus) -> dict:
    return QueueItem(
        id=str(uuid.uuid4()),
        title=data["name"],
        artist=data["all_artists"] or data["artist"],
        album=data["album_name"],
        language="Other",
        score=data["score"],
        status=status,
        spotify_id=data["spotify_id"],
        cover_url=data["art"],
        youtube_url=data["youtube_url"],
        fmt=data["fmt"],
        quality=data["quality"],
        year=data["year"],
        track_number=data["track_number"],
    ).model_dump()


def _bg_download(item_id: str, youtube_url: str, track_info: dict, fmt: str, quality: int) -> None:
    """Background thread: download audio, emit real progress via _DL_STATE."""
    def on_progress(pct: int):
        queue_routes._set_progress(item_id, pct)

    queue_routes.LOCAL_TEMP_DIR.mkdir(parents=True, exist_ok=True)

    # Block here until a slot frees up; limits concurrent YouTube pulls.
    with _DOWNLOAD_GATE:
        ok, msg, local_path = download_audio(
            youtube_url,
            str(queue_routes.LOCAL_TEMP_DIR),
            track_info,
            fmt=fmt,
            quality=quality,
            on_progress=on_progress,
        )

    # Detect geo-restriction for a friendlier error message
    if not ok and msg:
        msg_l = msg.lower()
        if any(k in msg_l for k in ("geo", "not available in your country", "region")):
            msg = "geo_restricted"

    if ok and local_path:
        audio_sha256 = _sha256_file(local_path)
        queue_routes._patch_item(
            item_id,
            local_path=local_path,
            audio_sha256=audio_sha256,
            status=QueueStatus.done,
        )
    else:
        queue_routes._patch_item(item_id, status=QueueStatus.error)

    queue_routes._set_progress(
        item_id,
        100 if ok else 0,
        state="done" if ok else "error",
        error=msg if not ok else None,
        sha256=audio_sha256 if ok and local_path else None,
    )


@router.post("/download/track")
async def download_single_track(payload: TrackDownloadRequest):
    """
    Non-blocking: resolve Spotify+YouTube (with scoring), return item_id immediately.
    If manual_review_enabled and score < 65: returns needs_review=true with top3 candidates.
    Otherwise starts background download; frontend polls GET /queue/{item_id}/progress (SSE).
    """
    deps = _check_dependencies()
    if not deps.ready:
        missing = [k for k, v in deps.model_dump().items() if v is False and k != "ready"]
        raise HTTPException(503, f"Server missing dependencies: {', '.join(missing)}")

    try:
        data = await asyncio.to_thread(
            _resolve_track, payload.spotify_id, payload.fmt, payload.quality
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, str(exc))

    cfg = _config.load_config() or {}
    manual_review = cfg.get("manual_review_enabled", False)
    needs_review = manual_review and data["score"] < REVIEW_SCORE_THRESHOLD

    status = QueueStatus.pending if needs_review else QueueStatus.downloading
    item = _make_queue_item(data, status)

    items = queue_routes._load()
    items.append(item)
    queue_routes._save(items)

    if needs_review:
        return {
            "item_id":      item["id"],
            "title":        data["name"],
            "artist":       data["all_artists"],
            "needs_review": True,
            "candidates":   data["candidates"],
            "score":        round(data["score"], 1),
        }

    queue_routes._set_progress(item["id"], 5)
    threading.Thread(
        target=_bg_download,
        args=(item["id"], data["youtube_url"], data["track_info"], payload.fmt, payload.quality),
        daemon=True,
    ).start()

    return {
        "item_id":      item["id"],
        "title":        data["name"],
        "artist":       data["all_artists"],
        "needs_review": False,
        "score":        round(data["score"], 1),
    }


@router.post("/download/track/confirm")
async def confirm_download(payload: ConfirmDownloadRequest):
    """
    Start download for an item that was held for manual review.
    Frontend calls this after the user picks a YouTube source.
    """
    items = queue_routes._load()
    item = next((it for it in items if it["id"] == payload.item_id), None)
    if not item:
        raise HTTPException(404, f"Queue item '{payload.item_id}' not found")

    item["youtube_url"] = payload.youtube_url
    item["status"] = QueueStatus.downloading
    queue_routes._update_item(items, item)

    track_info = {
        "name":          item.get("title", ""),
        "artist":        item.get("artist", ""),
        "album":         item.get("album", ""),
        "all_artists":   item.get("artist", ""),
        "album_art_url": item.get("cover_url"),
        "year":          item.get("year", ""),
        "track_number":  item.get("track_number", 0),
        "spotify_id":    item.get("spotify_id", ""),
        "spotify_url":   f"https://open.spotify.com/track/{item['spotify_id']}" if item.get("spotify_id") else "",
    }

    queue_routes._set_progress(item["id"], 5)
    threading.Thread(
        target=_bg_download,
        args=(item["id"], payload.youtube_url, track_info, item.get("fmt", "mp3"), item.get("quality", 320)),
        daemon=True,
    ).start()

    return {"item_id": item["id"], "ok": True}


@router.get("/download/{job_id}/status")
def download_status(job_id: str):
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
        if not job:
            raise HTTPException(404, f"Job '{job_id}' not found")
        return dict(job)


# ─── ZIP batch download ──────────────────────────────────────────────────────

_INVALID_FS_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def _safe_zip_name(name: str, used: set) -> str:
    """Sanitize a filename for inclusion in a zip; dedupe collisions."""
    base = _INVALID_FS_CHARS.sub("_", name).strip() or "track"
    stem, dot, ext = base.rpartition(".")
    candidate = base
    n = 1
    while candidate in used:
        if dot:
            candidate = f"{stem} ({n}).{ext}"
        else:
            candidate = f"{base} ({n})"
        n += 1
    used.add(candidate)
    return candidate


def _update_batch(job_id: str, **patch) -> None:
    with _BATCH_JOBS_LOCK:
        if job_id in _BATCH_JOBS:
            _BATCH_JOBS[job_id].update(patch)


def _run_batch_zip_job(job_id: str, spotify_ids: List[str], fmt: str, quality: int) -> None:
    """Resolve + download each track into a job temp dir, then zip them all.

    Respects _DOWNLOAD_GATE per track. Tracks progress in _BATCH_JOBS.
    Individual track failures don't abort the batch.
    """
    work_dir = queue_routes.LOCAL_TEMP_DIR / f"batch_{job_id}"
    work_dir.mkdir(parents=True, exist_ok=True)
    total = len(spotify_ids)
    _update_batch(job_id, state="downloading", progress={"done": 0, "total": total})

    done = 0
    errors = 0
    downloaded: List[str] = []

    def _one(sid: str) -> None:
        nonlocal done, errors
        try:
            data = _resolve_track(sid, fmt, quality)
            with _DOWNLOAD_GATE:
                ok, _msg, local_path = download_audio(
                    data["youtube_url"], str(work_dir), data["track_info"],
                    fmt=fmt, quality=quality,
                )
            if ok and local_path:
                downloaded.append(local_path)
            else:
                errors += 1
        except Exception:
            errors += 1
        finally:
            done += 1
            _update_batch(job_id, progress={"done": done, "total": total})

    # One thread per track; the download gate inside caps real concurrency.
    threads = [threading.Thread(target=_one, args=(sid,), daemon=True) for sid in spotify_ids]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    if not downloaded:
        shutil.rmtree(work_dir, ignore_errors=True)
        _update_batch(job_id, state="error", error="No tracks could be downloaded")
        return

    zip_path = queue_routes.LOCAL_TEMP_DIR / f"batch_{job_id}.zip"
    used: set = set()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_STORED) as zf:
        for path in downloaded:
            arcname = _safe_zip_name(Path(path).name, used)
            zf.write(path, arcname)

    shutil.rmtree(work_dir, ignore_errors=True)
    _update_batch(
        job_id, state="done", zip_path=str(zip_path),
        progress={"done": total, "total": total}, errors=errors,
    )


@router.post("/download/batch")
def download_batch(payload: BatchDownloadRequest):
    """Kick off a ZIP batch job for the given spotify_ids. Returns job_id."""
    deps = _check_dependencies()
    if not deps.ready:
        missing = [k for k, v in deps.model_dump().items() if v is False and k != "ready"]
        raise HTTPException(503, f"Server missing dependencies: {', '.join(missing)}")

    if not payload.spotify_ids:
        raise HTTPException(400, "spotify_ids is empty")

    job_id = str(uuid.uuid4())
    with _BATCH_JOBS_LOCK:
        _BATCH_JOBS[job_id] = {
            "id": job_id,
            "state": "queued",
            "progress": {"done": 0, "total": len(payload.spotify_ids)},
            "zip_path": None,
            "error": None,
            "errors": 0,
        }
    threading.Thread(
        target=_run_batch_zip_job,
        args=(job_id, payload.spotify_ids, payload.fmt, payload.quality),
        daemon=True,
    ).start()
    return {"job_id": job_id, "total": len(payload.spotify_ids)}


@router.get("/download/batch/{job_id}/progress")
async def batch_progress(job_id: str):
    """SSE of {done, total, state} until the zip is ready or the job errors."""
    async def events():
        deadline = asyncio.get_event_loop().time() + 1800  # 30-min safety timeout
        while asyncio.get_event_loop().time() < deadline:
            with _BATCH_JOBS_LOCK:
                job = dict(_BATCH_JOBS.get(job_id, {}))
            if not job:
                yield f"data: {json.dumps({'state': 'error', 'error': 'job not found'})}\n\n"
                return
            payload = {
                "state": job["state"],
                "done": job["progress"]["done"],
                "total": job["progress"]["total"],
                "errors": job.get("errors", 0),
                "error": job.get("error"),
            }
            yield f"data: {json.dumps(payload)}\n\n"
            if job["state"] in ("done", "error"):
                return
            await asyncio.sleep(0.4)
        yield f"data: {json.dumps({'state': 'error', 'error': 'timeout'})}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


@router.get("/download/batch/{job_id}/zip")
def batch_zip(job_id: str, background_tasks: BackgroundTasks):
    """Serve the finished zip and schedule cleanup of the file + job entry."""
    with _BATCH_JOBS_LOCK:
        job = dict(_BATCH_JOBS.get(job_id, {}))
    if not job:
        raise HTTPException(404, f"Batch job '{job_id}' not found")
    if job["state"] != "done" or not job.get("zip_path"):
        raise HTTPException(409, "Zip not ready yet.")

    zip_path = job["zip_path"]
    if not Path(zip_path).exists():
        raise HTTPException(404, "Zip file missing.")

    def _cleanup():
        try:
            Path(zip_path).unlink(missing_ok=True)
        except Exception:
            pass
        with _BATCH_JOBS_LOCK:
            _BATCH_JOBS.pop(job_id, None)

    background_tasks.add_task(_cleanup)
    return FileResponse(
        path=zip_path,
        filename="spotify-tracks.zip",
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="spotify-tracks.zip"'},
    )
