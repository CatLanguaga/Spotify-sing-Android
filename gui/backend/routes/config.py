import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from gui.backend.models import SpotifyConfig
from src.config import ConfigManager

router = APIRouter(tags=["config"])
_mgr = ConfigManager()


@router.get("/config")
def get_config():
    cfg = _mgr.load_config()
    return cfg if cfg else {}


@router.post("/config")
def save_config(body: SpotifyConfig):
    try:
        _mgr.save_config(
            spotify_client_id=body.client_id,
            spotify_client_secret=body.client_secret,
            download_folder=body.download_path,
            playlist_id=body.playlist_id,
        )
        return {"ok": True}
    except Exception as e:
        raise HTTPException(500, str(e))
