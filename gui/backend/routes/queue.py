import json
import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException

from gui.backend.models import QueueItem, QueuePatch, QueueStatus

router = APIRouter(tags=["queue"])

QUEUE_FILE = Path.home() / ".spotifytoyoutube" / "queue.json"


def _load() -> List[dict]:
    if QUEUE_FILE.exists():
        return json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
    return []


def _save(items: List[dict]):
    QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    QUEUE_FILE.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


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
            item["status"] = patch.status
            if patch.youtube_url:
                item["youtube_url"] = patch.youtube_url
            items[i] = item
            _save(items)
            return item
    raise HTTPException(404, f"Queue item '{item_id}' not found")


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
