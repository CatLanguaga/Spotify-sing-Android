import re
import sys
from time import monotonic
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.config import ConfigManager, MAX_TRACKS_PER_REQUEST
from src.spotify_client import SpotifyClient

router = APIRouter(tags=["spotify"])
_mgr = ConfigManager()

_PLAYLIST_INFO_TTL_SECONDS = 600
_PLAYLIST_INFO_CACHE: dict[str, tuple[float, dict]] = {}
_SPOTIFY_URL_RE = re.compile(
    r"open\.spotify\.com/(?:intl-[a-z]+/)?(track|album|playlist)/([A-Za-z0-9]+)"
)


def _parse_url(url: str) -> Optional[dict]:
    m = _SPOTIFY_URL_RE.search(url)
    if not m:
        return None
    return {"kind": m.group(1), "id": m.group(2)}


def _get_client() -> SpotifyClient:
    cfg = _mgr.load_config()
    if not cfg or not cfg.get("spotify_client_id"):
        raise HTTPException(400, "Spotify credentials not configured. Call POST /api/config first.")
    return SpotifyClient(cfg["spotify_client_id"], cfg["spotify_client_secret"])


def _clamp_limit(limit: int) -> int:
    return max(1, min(limit, MAX_TRACKS_PER_REQUEST))


def _get_playlist_info_cached(client: SpotifyClient, playlist_id: str) -> dict:
    now = monotonic()
    cached = _PLAYLIST_INFO_CACHE.get(playlist_id)
    if cached and now - cached[0] < _PLAYLIST_INFO_TTL_SECONDS:
        return cached[1]

    info = client.get_playlist_info(playlist_id) or {}
    _PLAYLIST_INFO_CACHE[playlist_id] = (now, info)
    return info


def _artist_genres_for_track(client: SpotifyClient, track: dict) -> list[str]:
    genre_lookup = getattr(client, "_get_artist_genres", None)
    if not genre_lookup:
        return []
    artist_ids = [a.get("id") for a in track.get("artists", []) if a.get("id")]
    genres_by_artist = genre_lookup(artist_ids)
    return sorted({
        genre
        for artist in track.get("artists", [])
        for genre in genres_by_artist.get(artist.get("id"), [])
    })


def _detect_track_language(
    client: SpotifyClient,
    track_name: str,
    album_name: str,
    artists: str,
    genres: Optional[list[str]] = None,
) -> str:
    detector = getattr(client, "_detect_language_smart", None)
    if not detector:
        return "Other"
    return detector(track_name, album_name, artists, genres or [])


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


@router.get("/spotify/resolve")
def resolve_url(
    url: str = Query(..., description="Spotify track / album / playlist URL"),
    offset: int = Query(0, ge=0),
    limit: int = Query(MAX_TRACKS_PER_REQUEST, ge=1),
):
    """Unified resolver. Returns kind + info + tracks (paginated for playlists)."""
    parsed = _parse_url(url)
    if not parsed:
        raise HTTPException(400, "URL must be a Spotify track, album, or playlist link.")

    client = _get_client()
    kind = parsed["kind"]
    sid = parsed["id"]
    limit = _clamp_limit(limit)

    if kind == "playlist":
        info = _get_playlist_info_cached(client, sid)
        tracks = client.get_playlist_tracks(sid, offset=offset, limit=limit)
        if not info and tracks is None:
            raise HTTPException(502, "Spotify playlist lookup failed. Check that the playlist is public and available.")
        tracks = tracks or []
        total = info.get("total_tracks") or info.get("total") or len(tracks) + offset
        return {
            "kind": "playlist",
            "info": info,
            "tracks": tracks,
            "total": total,
            "returned": len(tracks),
            "offset": offset,
        }

    if not client.authenticate():
        raise HTTPException(500, "Spotify auth failed")

    if kind == "track":
        try:
            t = client.sp.track(sid)
        except Exception as exc:
            raise HTTPException(502, f"Spotify track lookup failed: {exc}") from exc
        album = t.get("album", {}) or {}
        art = album.get("images", [{}])[0].get("url") if album.get("images") else None
        all_artists = ", ".join(a["name"] for a in t["artists"])
        genres = _artist_genres_for_track(client, t)
        track = {
            "name":          t["name"],
            "artist":        t["artists"][0]["name"] if t["artists"] else "Unknown",
            "all_artists":   all_artists,
            "duration_ms":   t.get("duration_ms", 0),
            "album":         album.get("name", ""),
            "album_art_url": art,
            "language":      _detect_track_language(client, t["name"], album.get("name", ""), all_artists, genres),
            "spotify_id":    t.get("id", ""),
            "year":          (album.get("release_date") or "")[:4],
            "track_number":  t.get("track_number", 1),
        }
        return {
            "kind": "track",
            "info": {
                "name": t["name"],
                "owner": t["artists"][0]["name"] if t["artists"] else "",
                "image_url": art,
                "total_tracks": 1,
            },
            "tracks": [track],
            "total": 1, "returned": 1, "offset": 0,
        }

    # album
    try:
        album = client.sp.album(sid)
    except Exception as exc:
        raise HTTPException(502, f"Spotify album lookup failed: {exc}") from exc
    art = album["images"][0]["url"] if album.get("images") else None
    tracks = []
    for t in album["tracks"]["items"]:
        all_artists = ", ".join(a["name"] for a in t["artists"])
        genres = _artist_genres_for_track(client, t)
        tracks.append({
            "name":          t["name"],
            "artist":        t["artists"][0]["name"] if t["artists"] else "Unknown",
            "all_artists":   all_artists,
            "duration_ms":   t.get("duration_ms", 0),
            "album":         album.get("name", ""),
            "album_art_url": art,
            "language":      _detect_track_language(client, t["name"], album.get("name", ""), all_artists, genres),
            "spotify_id":    t.get("id", ""),
            "year":          (album.get("release_date") or "")[:4],
            "track_number":  t.get("track_number", 1),
        })
    sliced = tracks[offset:offset + limit]
    return {
        "kind": "album",
        "info": {
            "name": album["name"],
            "owner": album["artists"][0]["name"] if album.get("artists") else "",
            "image_url": art,
            "total_tracks": len(tracks),
        },
        "tracks": sliced,
        "total": len(tracks),
        "returned": len(sliced),
        "offset": offset,
    }


@router.get("/spotify/status")
def spotify_status():
    cfg = _mgr.load_config()
    if not cfg or not cfg.get("spotify_client_id"):
        return {"connected": False, "reason": "No credentials configured"}
    client = SpotifyClient(cfg["spotify_client_id"], cfg["spotify_client_secret"])
    ok = client.authenticate()
    return {"connected": ok}
