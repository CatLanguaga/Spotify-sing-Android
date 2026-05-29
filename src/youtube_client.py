"""
YouTube search client using pytubefix (no API key required)
"""
import os
from contextlib import contextmanager

from pytubefix import Search

_PROXY_ENV_KEYS = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
)


@contextmanager
def without_env_proxies():
    previous = {key: os.environ.get(key) for key in _PROXY_ENV_KEYS}
    for key in _PROXY_ENV_KEYS:
        os.environ.pop(key, None)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


class YouTubeClient:
    def search_song_results(self, song_name: str, artist: str, limit: int = 5) -> list[dict]:
        """
        Search YouTube with a simple "song artist" query and return the top results.

        Returns a list of dicts: {title, url, duration, channel, thumbnail}
        """
        query = f"{song_name} {artist}".strip()
        seen_ids: set[str] = set()
        results: list[dict] = []

        try:
            with without_env_proxies():
                search = Search(query)
                videos = search.videos or []
        except Exception as exc:
            raise RuntimeError(f"YouTube search failed for '{query}': {exc}") from exc

        for v in videos:
            if len(results) >= limit:
                break
            vid_id = getattr(v, "video_id", None)
            if not vid_id or vid_id in seen_ids:
                continue
            seen_ids.add(vid_id)
            results.append({
                "title":     v.title or "",
                "url":       f"https://www.youtube.com/watch?v={vid_id}",
                "duration":  getattr(v, "length", None),
                "channel":   getattr(v, "author", None),
                "thumbnail": getattr(v, "thumbnail_url", None),
            })

        return results
    
    def get_video_info(self, video_url):
        """Get video information"""
        try:
            from pytubefix import YouTube

            with without_env_proxies():
                yt = YouTube(video_url)
            return {
                'title': yt.title,
                'author': yt.author,
                'length_seconds': yt.length
            }
        except Exception:
            return None
