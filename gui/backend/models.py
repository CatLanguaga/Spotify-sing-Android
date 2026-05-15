from enum import Enum
from typing import Optional

from pydantic import BaseModel


class QueueStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    downloading = "downloading"
    done = "done"
    error = "error"


class SpotifyConfig(BaseModel):
    client_id: str
    client_secret: str
    download_path: str
    playlist_id: str = ''
    auto_approve_threshold: int = 85
    min_score_to_show: int = 40


class QueueItem(BaseModel):
    id: str
    title: str
    artist: str
    album: str
    language: str
    score: float
    status: QueueStatus
    spotify_id: str
    cover_url: Optional[str] = None
    youtube_url: Optional[str] = None
    local_path: Optional[str] = None


class QueuePatch(BaseModel):
    status: QueueStatus
    youtube_url: Optional[str] = None


class ScriptRun(BaseModel):
    script: str
