import os
import sys
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from gui.backend.admin import audit as admin_audit
from gui.backend.admin import sessions as admin_sessions
from gui.backend.models import SpotifyConfig
from gui.backend.routes.admin import _client_ip, require_admin, require_admin_csrf
from src.config import ConfigManager

router = APIRouter(tags=["config"])
_mgr = ConfigManager()


def _flag(name: str, default: bool = True) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return raw.lower() in {"1", "true", "yes"}


@router.get("/config/public")
def get_public_config():
    cfg = _mgr.load_config() or {}
    return {
        "default_fmt": cfg.get("default_fmt", "mp3"),
        "default_quality": cfg.get("default_quality", 320),
        "manual_review_enabled": cfg.get("manual_review_enabled", False),
        "max_concurrent_downloads": cfg.get("max_concurrent_downloads", 3),
        "spotify_configured": bool(cfg.get("spotify_client_id") and cfg.get("spotify_client_secret")),
        # 11.5 stealth: when admin_footer_link=false the SPA hides the
        # "Admin" link from the footer so casual visitors don't see the panel.
        "admin_footer_link": _flag("ADMIN_FOOTER_LINK", default=True),
    }


@router.get("/config")
def get_config(_sess: admin_sessions.ValidSession = Depends(require_admin)):
    cfg = _mgr.load_config()
    return cfg if cfg else {}


@router.post("/config")
def save_config(
    body: SpotifyConfig,
    request: Request,
    sess: admin_sessions.ValidSession = Depends(require_admin_csrf),
):
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
        admin_audit.record(
            "config_write",
            result="ok",
            user_id=sess.user_id,
            ip=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
            meta={
                "default_fmt": body.default_fmt,
                "default_quality": body.default_quality,
                "max_concurrent_downloads": body.max_concurrent_downloads,
                "spotify_client_id_set": bool(body.client_id),
                "spotify_client_secret_set": bool(body.client_secret),
            },
        )
        return {"ok": True}
    except Exception as e:
        admin_audit.record(
            "config_write",
            result="fail",
            user_id=sess.user_id,
            ip=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
            meta={"error": str(e)[:200]},
        )
        raise HTTPException(500, str(e))
