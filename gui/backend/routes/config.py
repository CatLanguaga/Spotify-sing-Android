import sys
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from gui.backend.models import SpotifyConfig
from gui.backend.routes.admin import require_admin
from src.config import ConfigManager

router = APIRouter(tags=["config"])
_mgr = ConfigManager()


@router.get("/config/public")
def get_public_config():
    cfg = _mgr.load_config() or {}
    return {
        "default_fmt": cfg.get("default_fmt", "mp3"),
        "default_quality": cfg.get("default_quality", 320),
        "manual_review_enabled": cfg.get("manual_review_enabled", False),
        "max_concurrent_downloads": cfg.get("max_concurrent_downloads", 3),
        "spotify_configured": bool(cfg.get("spotify_client_id") and cfg.get("spotify_client_secret")),
    }


@router.get("/config")
def get_config(_admin: None = Depends(require_admin)):
    cfg = _mgr.load_config()
    return cfg if cfg else {}


@router.post("/config")
def save_config(body: SpotifyConfig, _admin: None = Depends(require_admin)):
    try:
        _mgr.save_config(
            spotify_client_id=body.client_id,
            spotify_client_secret=body.client_secret,
            download_folder=body.download_path,
            playlist_id=body.playlist_id,
            default_fmt=body.default_fmt,
            default_quality=body.default_quality,
            default_range_from=body.default_range_from,
            default_range_to=body.default_range_to,
            manual_review_enabled=body.manual_review_enabled,
            max_concurrent_downloads=body.max_concurrent_downloads,
        )
        return {"ok": True}
    except Exception as e:
        raise HTTPException(500, str(e))
