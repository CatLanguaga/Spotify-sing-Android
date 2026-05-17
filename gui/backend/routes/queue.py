import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

_ROOT = Path(os.environ.get("SPOTIFY_SYNC_ROOT", Path(__file__).resolve().parent.parent.parent.parent))
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from gui.backend.models import QueueItem, QueuePatch, QueueStatus
from src.downloader import download_audio

router = APIRouter(tags=["queue"])

QUEUE_FILE     = Path.home() / ".spotifytoyoutube" / "queue.json"
LOCAL_TEMP_DIR = _ROOT / "temp_downloads"
PHONE_MUSIC_DIR = "/storage/emulated/0/snaptube/download/Snaptube Audio"
_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


# ─── persistence ───────────────────────────────────────────────────────────────

def _load() -> List[dict]:
    if QUEUE_FILE.exists():
        return json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
    return []


def _save(items: List[dict]):
    QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    QUEUE_FILE.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def _update_item(items: List[dict], item: dict) -> None:
    for i, it in enumerate(items):
        if it["id"] == item["id"]:
            items[i] = item
            break
    _save(items)


# ─── ADB helper ────────────────────────────────────────────────────────────────

def _push_to_phone(local_path: str) -> tuple[bool, str]:
    remote = f"{PHONE_MUSIC_DIR}/{Path(local_path).name}"
    r = subprocess.run(
        ["adb", "push", local_path, remote],
        capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        creationflags=_NO_WINDOW,
    )
    return r.returncode == 0, r.stderr.strip()


# ─── routes ────────────────────────────────────────────────────────────────────

@router.get("/queue", response_model=List[QueueItem])
def get_queue():
    return _load()


@router.post("/queue", response_model=QueueItem)
def add_to_queue(item: QueueItem):
    items = _load()
    if not item.id:
        item.id = str(uuid.uuid4())
    items.append(item.model_dump())
    _save(items)
    return item


@router.patch("/queue/{item_id}", response_model=QueueItem)
def patch_queue_item(item_id: str, patch: QueuePatch):
    items = _load()
    for i, item in enumerate(items):
        if item["id"] == item_id:
            if patch.status is not None:
                item["status"] = patch.status
            if patch.youtube_url is not None:
                item["youtube_url"] = patch.youtube_url
            items[i] = item
            _save(items)
            return item
    raise HTTPException(404, f"Queue item '{item_id}' not found")


@router.post("/queue/{item_id}/download", response_model=QueueItem)
def download_queue_item(item_id: str):
    """
    Download a single queued track from its YouTube URL and push it to the phone via ADB.
    The item must have a youtube_url set (via the search flow).
    """
    items = _load()
    item = next((it for it in items if it["id"] == item_id), None)
    if not item:
        raise HTTPException(404, f"Queue item '{item_id}' not found")

    if not item.get("youtube_url"):
        raise HTTPException(400, "No YouTube URL — use the search flow first.")

    # Mark as downloading
    item["status"] = QueueStatus.downloading
    _update_item(items, item)

    track_info = {
        "name":          item.get("title", ""),
        "artist":        item.get("artist", ""),
        "album":         item.get("album", ""),
        "all_artists":   item.get("artist", ""),
        "album_art_url": item.get("cover_url"),
    }
    fmt     = item.get("fmt", "mp3")
    quality = item.get("quality", 320)

    LOCAL_TEMP_DIR.mkdir(parents=True, exist_ok=True)

    ok, msg, local_path = download_audio(
        item["youtube_url"], str(LOCAL_TEMP_DIR), track_info,
        fmt=fmt, quality=quality,
    )

    if not ok or not local_path:
        item["status"] = QueueStatus.error
        _update_item(items, item)
        raise HTTPException(500, f"Download failed: {msg}")

    pushed, push_err = _push_to_phone(local_path)

    # Clean up temp file regardless of push result
    try:
        Path(local_path).unlink(missing_ok=True)
    except Exception:
        pass

    if not pushed:
        item["status"] = QueueStatus.error
        _update_item(items, item)
        raise HTTPException(500, f"ADB push failed: {push_err}")

    item["status"] = QueueStatus.done
    _update_item(items, item)
    return item


@router.delete("/queue/{item_id}")
def remove_from_queue(item_id: str):
    items = _load()
    new_items = [i for i in items if i["id"] != item_id]
    if len(new_items) == len(items):
        raise HTTPException(404, f"Queue item '{item_id}' not found")
    _save(new_items)
    return {"ok": True}


@router.delete("/queue")
def clear_queue():
    _save([])
    return {"ok": True}


class QueuePatchFull(BaseModel):
    status: QueueStatus | None = None
    youtube_url: str | None = None
