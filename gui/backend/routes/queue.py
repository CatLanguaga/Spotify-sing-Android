import json
import os
import shutil
import sys
import uuid
from pathlib import Path
from typing import List
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

_ROOT = Path(os.environ.get("SPOTIFY_SYNC_ROOT", Path(__file__).resolve().parent.parent.parent.parent))
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from gui.backend.models import QueueItem, QueuePatch, QueueStatus
from src.config import ConfigManager
from src.downloader import download_audio

router = APIRouter(tags=["queue"])

QUEUE_FILE     = Path(os.environ.get("SPOTIFY_QUEUE_FILE", _ROOT / "data" / "queue.json"))
LOCAL_TEMP_DIR = _ROOT / "temp_downloads"
_config        = ConfigManager()


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
    """Download track to LOCAL_TEMP_DIR. Browser fetches via /file endpoint."""
    items = _load()
    item = next((it for it in items if it["id"] == item_id), None)
    if not item:
        raise HTTPException(404, f"Queue item '{item_id}' not found")

    if not item.get("youtube_url"):
        raise HTTPException(400, "No YouTube URL — use the search flow first.")

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

    item["local_path"] = local_path
    item["status"] = QueueStatus.done
    _update_item(items, item)
    return item


@router.get("/queue/{item_id}/file")
def serve_queue_file(item_id: str, background_tasks: BackgroundTasks):
    """Serve the downloaded file to the browser and schedule temp cleanup."""
    items = _load()
    item = next((it for it in items if it["id"] == item_id), None)
    if not item:
        raise HTTPException(404, f"Queue item '{item_id}' not found")

    local_path = item.get("local_path")
    if not local_path or not Path(local_path).exists():
        raise HTTPException(404, "File not found — download it first.")

    filename = Path(local_path).name
    # RFC 5987 encoding for non-ASCII filenames
    encoded_name = quote(filename)
    content_disposition = f"attachment; filename*=UTF-8''{encoded_name}"

    def _cleanup():
        try:
            Path(local_path).unlink(missing_ok=True)
        except Exception:
            pass
        # Clear local_path from queue item so frontend knows file is gone
        current = _load()
        for it in current:
            if it["id"] == item_id:
                it["local_path"] = None
                break
        _save(current)

    background_tasks.add_task(_cleanup)

    return FileResponse(
        path=local_path,
        filename=filename,
        headers={"Content-Disposition": content_disposition},
    )


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
