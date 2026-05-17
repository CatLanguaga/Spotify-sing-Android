"""
YouTube search client using pytubefix (no API key required)
"""
from pytubefix import Search


class YouTubeClient:
    def search_song_results(self, song_name: str, artist: str, duration_ms: int = 0, limit: int = 5) -> list[dict]:
        """
        Search YouTube and return the top `limit` results with metadata.

        Returns a list of dicts: {title, url, duration, channel, thumbnail}
        """
        queries = [
            f"{song_name} {artist} official audio",
            f"{song_name} {artist}",
        ]
        seen_ids: set[str] = set()
        results: list[dict] = []

        for query in queries:
            if len(results) >= limit:
                break
            try:
                search = Search(query)
                videos = search.videos or []
            except Exception:
                continue

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
            
            yt = YouTube(video_url)
            return {
                'title': yt.title,
                'author': yt.author,
                'length_seconds': yt.length
            }
        except Exception:
            return None
