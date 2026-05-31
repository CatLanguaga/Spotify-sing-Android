"""
YouTube search client with scoring algorithm for best-match selection.
Uses pytubefix (no API key required).
"""
import os
import re
from contextlib import contextmanager
from difflib import SequenceMatcher

from pytubefix import Search

_PROXY_ENV_KEYS = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
)

# Noise words to strip from video titles before comparison
_NOISE_RE = re.compile(
    r'\b(official|video|audio|lyric|lyrics|mv|hd|4k|music|explicit|visualizer|clip|vevo|full)\b',
    re.IGNORECASE,
)
# Strip featured artists from artist string
_FEAT_RE = re.compile(r'\s*(feat\.?|ft\.?|with\s)\s*.*', re.IGNORECASE)
# Non-alphanumeric (for normalization)
_SPECIAL_RE = re.compile(r'[^\w\s]')
# Words that indicate a non-original upload
_FLAG_WORDS = frozenset({'cover', 'remix', 'karaoke', '8d', 'slowed', 'sped up', 'nightcore', 'live'})


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


def _normalize_title(s: str) -> str:
    s = _NOISE_RE.sub('', s)
    s = _SPECIAL_RE.sub(' ', s)
    return ' '.join(s.lower().split())


def _normalize_artist(s: str) -> str:
    s = _FEAT_RE.sub('', s)
    s = _SPECIAL_RE.sub(' ', s)
    return ' '.join(s.lower().split())


def _str_sim(a: str, b: str) -> float:
    """0–1 similarity ratio via SequenceMatcher."""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _score_match(
    name: str,
    artist: str,
    duration_sec: float | None,
    yt: dict,
    is_live: bool = False,
) -> float:
    """
    Score a YouTube search result against a Spotify track (0–100).

    Components:
      - Duration match:  0–30 pts
      - Title similarity: 0–35 pts
      - Artist similarity: 0–25 pts
      - Channel "- Topic" bonus: +10 pts
      - Flag word penalty (cover/remix/karaoke/…): –20 pts
    """
    score = 0.0
    yt_title = yt.get('title', '')
    yt_channel = (yt.get('channel') or '').lower()
    yt_dur = yt.get('duration')

    # Duration component
    if duration_sec and yt_dur:
        diff = abs(duration_sec - yt_dur)
        if diff <= 1:    score += 30
        elif diff <= 3:  score += 25
        elif diff <= 5:  score += 18
        elif diff <= 10: score += 8
        # >10 s → 0 pts (may also be filtered out upstream)
    else:
        score += 15  # partial credit when no duration to compare

    # Title similarity
    clean_name = _normalize_title(name)
    clean_yt   = _normalize_title(yt_title)
    title_sim  = max(_str_sim(clean_name, clean_yt),
                     _str_sim(clean_name, (clean_yt + ' ' + yt_channel)))
    score += title_sim * 35

    # Artist similarity (check against YT title AND channel)
    clean_artist = _normalize_artist(artist)
    artist_sim   = max(_str_sim(clean_artist, clean_yt),
                       _str_sim(clean_artist, yt_channel))
    score += artist_sim * 25

    # Official label upload bonus
    if '- topic' in yt_channel:
        score += 10

    # Flag word penalty (apply only once)
    combined = (yt_title + ' ' + yt_channel).lower()
    for flag in _FLAG_WORDS:
        if flag in combined and not (flag == 'live' and is_live):
            score -= 20
            break

    return max(0.0, min(100.0, score))


class YouTubeClient:

    def _search_raw_query(self, query: str, limit: int = 5) -> list[dict]:
        """Execute a raw YouTube query and return up to `limit` deduped results."""
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
            vid_id = getattr(v, 'video_id', None)
            if not vid_id or vid_id in seen_ids:
                continue
            seen_ids.add(vid_id)
            results.append({
                'title':     v.title or '',
                'url':       f'https://www.youtube.com/watch?v={vid_id}',
                'duration':  getattr(v, 'length', None),
                'channel':   getattr(v, 'author', None),
                'thumbnail': getattr(v, 'thumbnail_url', None),
            })
        return results

    def search_song_results(
        self,
        song_name: str,
        artist: str,
        duration_ms: int = 0,
        limit: int = 5,
    ) -> list[dict]:
        """
        Simple search: returns YouTube results for "song artist" query.
        `duration_ms` is accepted but ignored (use find_best_match for scored search).
        """
        query = f'{song_name} {artist}'.strip()
        return self._search_raw_query(query, limit=limit)

    def search_raw(self, query: str, limit: int = 5) -> list[dict]:
        """Raw query search — used by the manual override modal."""
        return self._search_raw_query(query, limit=limit)

    def find_best_match(
        self,
        name: str,
        artist: str,
        duration_ms: int | None = None,
        limit: int = 5,
    ) -> tuple[dict | None, float, list[dict]]:
        """
        Multi-query search with scoring. Returns (best_result, best_score, top3_candidates).

        Query cascade:
          1. "{artist}" "{name}" topic   → prefer official label uploads
          2. "{artist}" "{name}" audio
          3. "{artist}" "{name}" lyrics
          4. {artist} {name}             → plain fallback

        Stops early if query 1 yields a result with score ≥ 90.
        Filters out results with duration >±10 s from Spotify's if duration_ms is known.
        """
        duration_sec = (duration_ms / 1000) if duration_ms else None
        is_live = 'live' in name.lower()

        queries = [
            f'"{artist}" "{name}" topic',
            f'"{artist}" "{name}" audio',
            f'"{artist}" "{name}" lyrics',
            f'{artist} {name}',
        ]

        all_results: list[dict] = []
        seen_ids: set[str] = set()

        for i, query in enumerate(queries):
            try:
                batch = self._search_raw_query(query, limit=limit)
            except Exception:
                continue

            for r in batch:
                url = r.get('url', '')
                vid_id = url.split('v=')[-1] if 'v=' in url else url
                if vid_id in seen_ids:
                    continue
                seen_ids.add(vid_id)

                # Duration filter: skip if more than ±10 s off (only when duration is known)
                yt_dur = r.get('duration')
                if duration_sec and yt_dur and abs(duration_sec - yt_dur) > 10:
                    continue

                r['score'] = round(_score_match(name, artist, duration_sec, r, is_live), 1)
                all_results.append(r)

            # Early exit on first query if we already have a high-confidence match
            if i == 0 and all_results:
                best = max(all_results, key=lambda x: x['score'])
                if best['score'] >= 90:
                    top3 = sorted(all_results, key=lambda x: x['score'], reverse=True)[:3]
                    return best, best['score'], top3

        if not all_results:
            return None, 0.0, []

        ranked = sorted(all_results, key=lambda x: x['score'], reverse=True)
        best   = ranked[0]
        return best, best['score'], ranked[:3]

    def get_video_info(self, video_url):
        """Get basic video information."""
        try:
            from pytubefix import YouTube
            with without_env_proxies():
                yt = YouTube(video_url)
            return {'title': yt.title, 'author': yt.author, 'length_seconds': yt.length}
        except Exception:
            return None
