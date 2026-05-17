import os
import sys
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

_ROOT = Path(os.environ.get("SPOTIFY_SYNC_ROOT", Path(__file__).resolve().parent.parent.parent.parent))
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.youtube_client import YouTubeClient

router = APIRouter(tags=["youtube"])
_yt = YouTubeClient()


class YTResult(BaseModel):
    title: str
    url: str
    duration: Optional[int] = None
    channel: Optional[str] = None
    thumbnail: Optional[str] = None


@router.get("/youtube/search", response_model=List[YTResult])
def search_youtube(
    song: str = Query(...),
    artist: str = Query(""),
    duration_ms: Optional[int] = Query(None),
    limit: int = Query(5, ge=1, le=10),
):
    """Return up to `limit` YouTube results for the given track."""
    try:
        results = _yt.search_song_results(song, artist, duration_ms or 0, limit=limit)
        return results
    except Exception as e:
        raise HTTPException(500, str(e))
