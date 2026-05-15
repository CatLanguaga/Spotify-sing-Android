import sys
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

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
    song: str = Query(..., description="Track name"),
    artist: str = Query("", description="Artist name"),
    duration_ms: Optional[int] = Query(None, description="Expected duration in ms"),
):
    try:
        url = _yt.search_song(song, artist, duration_ms or 0)
        if not url:
            return []
        return [YTResult(title=f"{song} - {artist}", url=url)]
    except Exception as e:
        raise HTTPException(500, str(e))
