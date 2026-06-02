import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

# SPOTIFY_SYNC_ROOT se setea desde app.py (desarrollo y exe).
# Fallback para cuando se corre main.py directamente en dev.
_ROOT = Path(os.environ.get("SPOTIFY_SYNC_ROOT", Path(__file__).parent.parent.parent))
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from gui.backend.routes import admin, config, download, queue, scripts, spotify, youtube
from gui.backend.ws_runner import router as ws_router


class SPAStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404:
                return await super().get_response("index.html", scope)
            raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    deps = download._check_dependencies()
    if not deps.ready:
        missing = [k for k, v in deps.model_dump().items() if v is False and k != "ready"]
        print(f"[startup] WARNING: missing dependencies -> {', '.join(missing)}. "
              f"/api/download/direct will return 503 until installed.", flush=True)
    # En esta rama el frontend se sirve por Vite dev (http://localhost:5173).
    # No auto-abrimos navegador desde el backend para no levantar la vista vieja del dist.
    yield


app = FastAPI(title="Spotify Sync Manager", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
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
    uvicorn.run("gui.backend.main:app", host="0.0.0.0", port=8000, reload=True)
