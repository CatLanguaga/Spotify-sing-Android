import os
import sys
import webbrowser
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# SPOTIFY_SYNC_ROOT se setea desde app.py (desarrollo y exe).
# Fallback para cuando se corre main.py directamente en dev.
_ROOT = Path(os.environ.get("SPOTIFY_SYNC_ROOT", Path(__file__).parent.parent.parent))
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from gui.backend.routes import adb, compare, config, queue, scripts, spotify, youtube
from gui.backend.ws_runner import router as ws_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Skip browser launch when running inside Tauri (it manages the window itself).
    if not os.environ.get("SPOTIFY_SYNC_TAURI"):
        webbrowser.open("http://localhost:8000")
    yield


app = FastAPI(title="Spotify Sync Manager", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(adb.router, prefix="/api")
app.include_router(config.router, prefix="/api")
app.include_router(compare.router, prefix="/api")
app.include_router(queue.router, prefix="/api")
app.include_router(youtube.router, prefix="/api")
app.include_router(scripts.router, prefix="/api")
app.include_router(spotify.router, prefix="/api")
app.include_router(ws_router)

stitch_dir = _ROOT / "gui" / "stitch"
if stitch_dir.exists():
    app.mount("/stitch", StaticFiles(directory=stitch_dir), name="stitch")

# Serve the built React frontend when the dist/ folder exists (production / Tauri mode).
# Must be mounted last so API routes take priority.
frontend_dist = _ROOT / "gui" / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("gui.backend.main:app", host="0.0.0.0", port=8000, reload=True)
