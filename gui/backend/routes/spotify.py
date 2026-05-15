import sys
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.config import ConfigManager
from src.spotify_client import SpotifyClient

router = APIRouter(tags=["spotify"])
_mgr = ConfigManager()


def _get_client() -> SpotifyClient:
    cfg = _mgr.load_config()
    if not cfg or not cfg.get("spotify_client_id"):
        raise HTTPException(400, "Spotify credentials not configured. Call POST /api/config first.")
    return SpotifyClient(cfg["spotify_client_id"], cfg["spotify_client_secret"])


@router.get("/spotify/playlist/{playlist_id}")
def get_playlist(
    playlist_id: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
):
    client = _get_client()

    # Paginate internally since Spotify API caps at 100 per request
    all_tracks = []
    remaining = limit
    current_offset = offset
    while remaining > 0:
        batch = min(remaining, 100)
        tracks = client.get_playlist_tracks(playlist_id, offset=current_offset, limit=batch)
        if tracks is None:
            raise HTTPException(500, "Failed to fetch playlist. Check credentials or playlist ID.")
        all_tracks.extend(tracks)
        if len(tracks) < batch:
            break  # reached end of playlist
        remaining -= batch
        current_offset += batch

    info = client.get_playlist_info(playlist_id) or {}
    return {"info": info, "tracks": all_tracks, "count": len(all_tracks)}


@router.get("/spotify/search")
def search_track(
    track: str = Query(...),
    artist: str = Query(""),
):
    client = _get_client()
    results = client.search_track(track, artist)
    if results is None:
        raise HTTPException(500, "Spotify search failed.")
    return {"results": results}


@router.get("/spotify/status")
def spotify_status():
    cfg = _mgr.load_config()
    if not cfg or not cfg.get("spotify_client_id"):
        return {"connected": False, "reason": "No credentials configured"}
    client = SpotifyClient(cfg["spotify_client_id"], cfg["spotify_client_secret"])
    ok = client.authenticate()
    return {"connected": ok}
