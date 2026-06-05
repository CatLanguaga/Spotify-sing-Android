import logging
import os
import sys
import threading
import traceback
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

# SPOTIFY_SYNC_ROOT se setea desde app.py (desarrollo y exe).
# Fallback para cuando se corre main.py directamente en dev.
_ROOT = Path(os.environ.get("SPOTIFY_SYNC_ROOT", Path(__file__).parent.parent.parent))
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# ─── Logging a archivo ──────────────────────────────────────────────────────
_LOG_DIR = Path(os.environ.get("SPOTIFY_LOG_DIR", _ROOT / "logs"))
_LOG_DIR.mkdir(parents=True, exist_ok=True)
_LOG_FILE = _LOG_DIR / "app.log"

_log_level = os.environ.get("SPOTIFY_LOG_LEVEL", "INFO").upper()
_formatter = logging.Formatter(
    "%(asctime)s %(levelname)s [%(name)s] [%(threadName)s] %(message)s"
)
_file_handler = RotatingFileHandler(
    _LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
)
_file_handler.setFormatter(_formatter)
_stream_handler = logging.StreamHandler()
_stream_handler.setFormatter(_formatter)

_root_logger = logging.getLogger()
_root_logger.setLevel(_log_level)
# Evitar handlers duplicados en reload de uvicorn
if not any(isinstance(h, RotatingFileHandler) for h in _root_logger.handlers):
    _root_logger.addHandler(_file_handler)
if not any(isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler)
           for h in _root_logger.handlers):
    _root_logger.addHandler(_stream_handler)

for _name in ("uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"):
    _lg = logging.getLogger(_name)
    _lg.handlers = []
    _lg.propagate = True

# Uncaught exceptions
def _excepthook(exc_type, exc, tb):
    logging.getLogger("uncaught").critical(
        "Unhandled exception", exc_info=(exc_type, exc, tb)
    )

sys.excepthook = _excepthook

def _thread_excepthook(args):
    logging.getLogger("thread").critical(
        "Unhandled thread exception in %s", args.thread.name,
        exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
    )

threading.excepthook = _thread_excepthook

logger = logging.getLogger("spotify-sync")
logger.info("Logging inicializado → %s (level=%s)", _LOG_FILE, _log_level)

from gui.backend.routes import admin, config, download, queue, scripts, spotify, youtube
from gui.backend.ws_runner import router as ws_router
from gui.backend.admin.ratelimit import limiter as _admin_limiter
from gui.backend.admin.headers import SecurityHeadersMiddleware
from gui.backend.admin.guards import AdminGuardMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler


class SPAStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404:
                return await super().get_response("index.html", scope)
            raise


def _seed_admin_from_env() -> None:
    """One-shot migration: if DB has no users but ADMIN_PASSWORD env is set,
    seed user 'admin' with that password. Env is then ignored on subsequent boots."""
    from gui.backend.admin import users as admin_users

    legacy_pw = os.environ.get("ADMIN_PASSWORD") or os.environ.get("SPOTIFY_ADMIN_PASSWORD")
    if not legacy_pw:
        return
    if admin_users.count_users() > 0:
        return
    try:
        admin_users.create_user("admin", legacy_pw, skip_strength_check=True)
        logger.warning("legacy env seed completed: admin user created from ADMIN_PASSWORD env. "
                       "Consider rotating via admin_cli reset-password and removing the env var.")
    except Exception as e:
        logger.error("Admin env seed failed: %s", e)


def _migrate_config_encryption() -> None:
    """Upgrade plaintext spotify_client_secret in config.json to at-rest ciphertext."""
    try:
        from src.config import ConfigManager
        migrated = ConfigManager().migrate_at_rest_encryption()
        if migrated:
            logger.warning("Upgraded config.json: spotify_client_secret now encrypted at rest.")
    except Exception as e:
        logger.error("At-rest config migration failed: %s", e)


def _install_youtube_cookies() -> None:
    """If admin uploaded cookies, install the pytubefix monkey-patch so every
    youtube.com / googlevideo.com request carries the Cookie header."""
    try:
        from gui.backend.admin import yt_cookies
        yt_cookies.install_cookie_patch()
        if yt_cookies.is_present():
            logger.info("YouTube cookies present at startup — injection patch active.")
    except Exception as e:
        logger.warning("YouTube cookies setup failed: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _seed_admin_from_env()
    _migrate_config_encryption()
    _install_youtube_cookies()
    deps = download._check_dependencies()
    if not deps.ready:
        missing = [k for k, v in deps.model_dump().items() if v is False and k != "ready"]
        print(f"[startup] WARNING: missing dependencies -> {', '.join(missing)}. "
              f"/api/download/direct will return 503 until installed.", flush=True)
    # En esta rama el frontend se sirve por Vite dev (http://localhost:5173).
    # No auto-abrimos navegador desde el backend para no levantar la vista vieja del dist.
    yield


app = FastAPI(title="Spotify Sync Manager", lifespan=lifespan)

# slowapi limiter for /admin/login
app.state.limiter = _admin_limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.middleware("http")
async def _log_requests(request: Request, call_next):
    log = logging.getLogger("http")
    try:
        response = await call_next(request)
        log.info("%s %s -> %s", request.method, request.url.path, response.status_code)
        return response
    except Exception:
        log.exception("Unhandled error on %s %s", request.method, request.url.path)
        raise


app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(AdminGuardMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8001",
        "http://127.0.0.1:8001",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.include_router(admin.router, prefix="/api")
app.include_router(config.router, prefix="/api")
app.include_router(queue.router, prefix="/api")
app.include_router(youtube.router, prefix="/api")
app.include_router(scripts.router, prefix="/api")
app.include_router(spotify.router, prefix="/api")
app.include_router(download.router, prefix="/api")

app.include_router(ws_router)


@app.get("/health")
def health():
    """Liveness probe for Coolify/Docker healthcheck. No external deps checked."""
    return {"status": "ok"}

stitch_dir = _ROOT / "gui" / "stitch"
if stitch_dir.exists():
    app.mount("/stitch", StaticFiles(directory=stitch_dir), name="stitch")

# Serve the built React frontend when the dist/ folder exists (production / Tauri mode).
# Must be mounted last so API routes take priority.
frontend_dist = _ROOT / "gui" / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", SPAStaticFiles(directory=frontend_dist, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("gui.backend.main:app", host="0.0.0.0", port=8001, reload=True)
