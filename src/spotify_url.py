import re
from typing import Optional
from urllib.parse import urlparse

import requests

from src.youtube_client import without_env_proxies

SPOTIFY_URL_RE = re.compile(
    r"open\.spotify\.com/(?:intl-[a-z]+/)?(track|album|playlist)/([A-Za-z0-9]+)"
)

SHORTLINK_HOSTS = {"spotify.link", "spotify.app.link"}


def parse_spotify_url(url: str) -> Optional[dict]:
    match = SPOTIFY_URL_RE.search(url)
    if not match:
        return None
    return {"kind": match.group(1), "id": match.group(2), "url": url}


def normalize_spotify_url(url: str) -> str:
    raw = (url or "").strip()
    if raw.startswith(("spotify.link/", "spotify.app.link/")):
        raw = f"https://{raw}"
    parsed = urlparse(raw)
    host = parsed.netloc.lower()

    if host in SHORTLINK_HOSTS:
        with without_env_proxies():
            response = requests.get(raw, allow_redirects=True, timeout=10)
        final_url = response.url
        if not parse_spotify_url(final_url):
            raise ValueError("Spotify shortlink did not resolve to a supported Spotify URL.")
        return final_url

    return raw


def resolve_spotify_url(url: str) -> Optional[dict]:
    normalized = normalize_spotify_url(url)
    return parse_spotify_url(normalized)
