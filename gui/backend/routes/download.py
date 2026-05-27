import os
import re
import shutil
import sys
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

_ROOT = Path(os.environ.get("SPOTIFY_SYNC_ROOT", Path(__file__).resolve().parent.parent.parent.parent))
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from gui.backend.models import QueueItem, QueueStatus
from gui.backend.routes import queue as queue_routes
from src.config import ConfigManager
from src.downloader import download_audio
from src.spotify_client import SpotifyClient
from src.youtube_client import YouTubeClient

router = APIRouter(tags=["download"])

_config = ConfigManager()

# In-memory job store. Keyed by job_id.
_JOBS: Dict[str, dict] = {}
_JOBS_LOCK = threading.Lock()

_SPOTIFY_URL_RE = re.compile(
    r"open\.spotify\.com/(?:intl-[a-z]+/)?(track|album|playlist)/([A-Za-z0-9]+)"
)


class DirectDownloadRequest(BaseModel):
    url: str
    fmt: str = "mp3"
    quality: int = 320


class TrackDownloadRequest(BaseModel):
    spotify_id: str
    fmt: str = "mp3"
    quality: int = 320


class DependencyStatus(BaseModel):
    ffmpeg: bool
    pytubefix: bool
    ready: bool


def _detect(url: str) -> Optional[dict]:
    m = _SPOTIFY_URL_RE.search(url)
    if not m:
        return None
    return {"type": m.group(1), "id": m.group(2)}


def _get_spotify_client() -> SpotifyClient:
    cfg = _config.load_config()
    if not cfg or not cfg.get("spotify_client_id"):
        raise HTTPException(400, "Spotify credentials not configured.")
    return SpotifyClient(cfg["spotify_client_id"], cfg["spotify_client_secret"])


def _check_dependencies() -> DependencyStatus:
    ffmpeg_ok = shutil.which("ffmpeg") is not None
    try:
        import pytubefix  # noqa: F401
        pytubefix_ok = True
    except Exception:
        pytubefix_ok = False
    return DependencyStatus(
        ffmpeg=ffmpeg_ok,
        pytubefix=pytubefix_ok,
        ready=ffmpeg_ok and pytubefix_ok,
    )


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
    )
    return item.model_dump()


def _run_direct_job(job_id: str, url: str, fmt: str, quality: int) -> None:
    deps = _check_dependencies()
    if not deps.ready:
        missing = [k for k, v in deps.model_dump().items() if v is False and k != "ready"]
        _update_job(job_id, state="error", error=f"Missing dependencies: {', '.join(missing)}")
        return

    parsed = _detect(url)
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

    parsed = _detect(payload.url)
    if not parsed:
        raise HTTPException(400, "URL must be a Spotify track, album, or playlist link.")

    job_id = _new_job(payload.url, parsed["type"])
    background_tasks.add_task(_run_direct_job, job_id, payload.url, payload.fmt, payload.quality)
    return {"job_id": job_id, "kind": parsed["type"]}


@router.post("/download/track")
def download_single_track(payload: TrackDownloadRequest):
    """Synchronous one-shot: spotify_id -> YT search -> download -> return queue item_id."""
    deps = _check_dependencies()
    if not deps.ready:
        missing = [k for k, v in deps.model_dump().items() if v is False and k != "ready"]
        raise HTTPException(503, f"Server missing dependencies: {', '.join(missing)}")

    client = _get_spotify_client()
    if not client.authenticate():
        raise HTTPException(500, "Spotify auth failed")

    try:
        t = client.sp.track(payload.spotify_id)
    except Exception as exc:
        raise HTTPException(404, f"Spotify track lookup failed: {exc}")

    album = t.get("album", {}) or {}
    art = album.get("images", [{}])[0].get("url") if album.get("images") else None
    name = t["name"]
    artist = t["artists"][0]["name"] if t["artists"] else "Unknown"
    all_artists = ", ".join(a["name"] for a in t["artists"])
    duration_ms = t.get("duration_ms", 0)

    yt = YouTubeClient()
    try:
        results = yt.search_song_results(name, artist, duration_ms, limit=1)
    except Exception as exc:
        raise HTTPException(502, f"YouTube search failed: {exc}")

    if not results:
        raise HTTPException(404, "No YouTube match found.")

    youtube_url = results[0]["url"]

    item = QueueItem(
        id=str(uuid.uuid4()),
        title=name,
        artist=all_artists or artist,
        album=album.get("name", ""),
        language="Other",
        score=0.0,
        status=QueueStatus.downloading,
        spotify_id=payload.spotify_id,
        cover_url=art,
        youtube_url=youtube_url,
        fmt=payload.fmt,
        quality=payload.quality,
    ).model_dump()

    items = queue_routes._load()
    items.append(item)
    queue_routes._save(items)

    track_info = {
        "name":          name,
        "artist":        artist,
        "album":         album.get("name", ""),
        "all_artists":   all_artists,
        "album_art_url": art,
    }
    queue_routes.LOCAL_TEMP_DIR.mkdir(parents=True, exist_ok=True)

    ok, msg, local_path = download_audio(
        youtube_url,
        str(queue_routes.LOCAL_TEMP_DIR),
        track_info,
        fmt=payload.fmt,
        quality=payload.quality,
    )

    if not ok or not local_path:
        item["status"] = QueueStatus.error
        queue_routes._update_item(items, item)
        raise HTTPException(500, f"Download failed: {msg}")

    item["local_path"] = local_path
    item["status"] = QueueStatus.done
    queue_routes._update_item(items, item)
    return {"item_id": item["id"], "title": name, "artist": all_artists}


@router.get("/download/{job_id}/status")
def download_status(job_id: str):
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
        if not job:
            raise HTTPException(404, f"Job '{job_id}' not found")
        return dict(job)
