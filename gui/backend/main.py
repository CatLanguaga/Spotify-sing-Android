import asyncio
import sys
import webbrowser
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from gui.backend.routes import adb, compare, config, queue, scripts, spotify, youtube
from gui.backend.ws_runner import router as ws_router


@asynccontextmanager
async def lifespan(app: FastAPI):
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

stitch_dir = Path(__file__).parent.parent / "stitch"
if stitch_dir.exists():
    app.mount("/stitch", StaticFiles(directory=stitch_dir), name="stitch")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("gui.backend.main:app", host="0.0.0.0", port=8000, reload=True)
