"""YouTube cookies management — bypass datacenter-IP bot detection.

Flow:
    1. Admin uploads cookies.txt (Netscape format) from a dedicated YT account.
    2. We parse → MozillaCookieJar, verify auth cookies present.
    3. Encrypt with admin.crypto and persist to data/youtube_cookies.enc.
    4. On startup (or after upload) install_cookie_patch() monkey-patches
       pytubefix.request._execute_request so every youtube.com request
       carries the Cookie header.

The monkey-patch is intentionally narrow: only youtube.com / googlevideo.com
URLs get the Cookie header — never leaked elsewhere. It is idempotent: the
patched callable is tagged so subsequent installs are no-ops.

Storage layout:
    {data_dir}/youtube_cookies.enc        — encrypted cookies.txt blob
    {data_dir}/youtube_cookies.meta.json  — { uploaded_at, last_validated_at, last_status }

Audit actions emitted:
    youtube_cookies_upload, youtube_cookies_delete, youtube_cookies_invalid
"""
from __future__ import annotations

import http.cookiejar as _cj
import io
import json
import logging
import threading
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from . import audit as admin_audit
from . import crypto
from .db import DB_PATH

log = logging.getLogger(__name__)

_DATA_DIR = DB_PATH.parent
_BLOB_PATH = _DATA_DIR / "youtube_cookies.enc"
_META_PATH = _DATA_DIR / "youtube_cookies.meta.json"

# Cookies that must be present in a valid logged-in YouTube session.
_REQUIRED_COOKIE_NAMES: tuple[str, ...] = ("SID", "HSID", "SSID")
# At least one of these must also be present (newer Google sessions).
_REQUIRED_ANY_OF: tuple[str, ...] = ("__Secure-3PSID", "__Secure-1PSID", "APISID", "SAPISID")

_YT_HOST_FRAGMENTS = (".youtube.com", "youtube.com", ".googlevideo.com", "googlevideo.com")

_lock = threading.RLock()
_cached_header: Optional[str] = None
_patched: bool = False


class CookiesError(Exception):
    pass


# ── Parsing / validation ────────────────────────────────────────────────
def parse_netscape(content: str) -> _cj.MozillaCookieJar:
    """Parse Netscape-format cookies.txt content into a CookieJar.

    Raises CookiesError on malformed input or missing auth cookies.
    """
    if not content or not isinstance(content, str):
        raise CookiesError("Empty cookies content.")
    jar = _cj.MozillaCookieJar()
    # MozillaCookieJar expects a file path; emulate with a temp file in memory
    # by writing into a NamedTemporaryFile is heavyweight. Parse manually.
    lines = content.splitlines()
    if not any(l.strip().startswith("# Netscape HTTP Cookie File") or l.startswith("# HTTP Cookie File")
               for l in lines[:5]):
        # Tolerate missing header — some exporters omit it. Still attempt parse.
        log.debug("Netscape header missing from uploaded cookies — attempting tolerant parse.")
    parsed = 0
    for raw in lines:
        line = raw.rstrip("\n").rstrip("\r")
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) != 7:
            continue
        domain, flag, path, secure, expires, name, value = parts
        try:
            expires_int = int(expires) if expires.strip() else 0
        except ValueError:
            continue
        c = _cj.Cookie(
            version=0,
            name=name,
            value=value,
            port=None,
            port_specified=False,
            domain=domain,
            domain_specified=domain.startswith("."),
            domain_initial_dot=domain.startswith("."),
            path=path,
            path_specified=True,
            secure=(secure.upper() == "TRUE"),
            expires=(expires_int or None),
            discard=False,
            comment=None,
            comment_url=None,
            rest={},
            rfc2109=False,
        )
        jar.set_cookie(c)
        parsed += 1
    if parsed == 0:
        raise CookiesError("No valid cookie lines parsed (check Netscape format).")

    names = {c.name for c in jar}
    missing_required = [n for n in _REQUIRED_COOKIE_NAMES if n not in names]
    if missing_required:
        raise CookiesError(
            "Missing required Google auth cookies: " + ", ".join(missing_required)
            + ". Make sure you exported cookies while logged into youtube.com."
        )
    if not any(n in names for n in _REQUIRED_ANY_OF):
        raise CookiesError(
            "None of the expected secure session cookies present "
            f"({', '.join(_REQUIRED_ANY_OF)}). Re-export from a fresh login."
        )
    return jar


def _cookie_header_for_youtube(jar: _cj.MozillaCookieJar) -> str:
    """Build a single Cookie: header for youtube.com from the jar."""
    pairs: list[str] = []
    for c in jar:
        domain = (c.domain or "").lower()
        if not any(frag in domain for frag in _YT_HOST_FRAGMENTS):
            continue
        pairs.append(f"{c.name}={c.value}")
    return "; ".join(pairs)


# ── Persistence ─────────────────────────────────────────────────────────
def _write_meta(uploaded_at: int, validated_at: Optional[int], status: str) -> None:
    meta = {
        "uploaded_at": uploaded_at,
        "last_validated_at": validated_at,
        "last_status": status,
    }
    _META_PATH.write_text(json.dumps(meta, indent=2), encoding="utf-8")


def read_meta() -> dict:
    if not _META_PATH.exists():
        return {}
    try:
        return json.loads(_META_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def is_present() -> bool:
    return _BLOB_PATH.exists() and _BLOB_PATH.stat().st_size > 0


def save_cookies(content: str) -> dict:
    """Validate + encrypt + persist. Returns the new meta dict.

    Does NOT install the monkey-patch — caller decides when to call install_cookie_patch().
    """
    jar = parse_netscape(content)  # raises CookiesError
    header = _cookie_header_for_youtube(jar)
    if not header:
        raise CookiesError("No youtube.com cookies in the file — wrong domain export?")

    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    blob = crypto.encrypt(content)
    _BLOB_PATH.write_text(blob, encoding="ascii")
    now = int(time.time())
    _write_meta(uploaded_at=now, validated_at=None, status="uploaded")

    with _lock:
        global _cached_header
        _cached_header = header

    return read_meta()


def delete_cookies() -> bool:
    removed = False
    if _BLOB_PATH.exists():
        _BLOB_PATH.unlink()
        removed = True
    if _META_PATH.exists():
        _META_PATH.unlink()
    with _lock:
        global _cached_header
        _cached_header = None
    return removed


def load_cookies_header(force_refresh: bool = False) -> Optional[str]:
    """Decrypt the persisted blob and return the YT Cookie header value.

    Returns None when no cookies are stored or decryption fails.
    """
    global _cached_header
    with _lock:
        if _cached_header is not None and not force_refresh:
            return _cached_header
        if not is_present():
            return None
        try:
            blob = _BLOB_PATH.read_text(encoding="ascii")
            content = crypto.decrypt(blob)
            jar = parse_netscape(content)
            _cached_header = _cookie_header_for_youtube(jar)
        except Exception as e:
            log.error("Failed to load YouTube cookies: %s", e)
            _cached_header = None
        return _cached_header


def mark_invalid(reason: str = "unknown") -> None:
    """Called from the download path when cookies appear expired / rejected.

    Updates meta to surface "cookies expired — re-upload" badge in admin UI
    and clears the cached header so subsequent requests fall back to no-cookie.
    """
    meta = read_meta()
    now = int(time.time())
    meta["last_validated_at"] = now
    meta["last_status"] = f"invalid:{reason}"
    try:
        _META_PATH.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    except Exception:
        pass
    with _lock:
        global _cached_header
        _cached_header = None
    try:
        admin_audit.record("youtube_cookies_invalid", result="info",
                           meta={"reason": reason[:200]})
    except Exception:
        pass


# ── Validation against a live YouTube request ───────────────────────────
def validate_against_youtube(test_url: str = "https://www.youtube.com/watch?v=dQw4w9WgXcQ") -> tuple[bool, str]:
    """Attempt a minimal request through pytubefix using the loaded cookies.

    Returns (ok, message). Caller decides whether to persist meta/status.
    Patches must already be installed for this to use cookies.
    """
    try:
        from pytubefix import YouTube
    except Exception as e:
        return False, f"pytubefix import failed: {e}"
    try:
        yt = YouTube(test_url, client="WEB")
        title = yt.title  # touches network → triggers cookie injection
        ok = bool(title)
        return ok, f"OK title={title!r}" if ok else "empty title"
    except Exception as e:
        msg = str(e)
        lower = msg.lower()
        if "bot" in lower or "sign in" in lower or "consent" in lower:
            return False, f"bot detection / consent wall: {msg[:200]}"
        return False, f"validation error: {msg[:200]}"


def record_validation_result(ok: bool, message: str) -> None:
    meta = read_meta()
    meta["last_validated_at"] = int(time.time())
    meta["last_status"] = "valid" if ok else f"invalid:{message[:160]}"
    try:
        _META_PATH.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    except Exception:
        pass


# ── pytubefix monkey-patch ──────────────────────────────────────────────
def install_cookie_patch() -> bool:
    """Patch pytubefix.request._execute_request to inject Cookie: header
    when the target URL is youtube.com / googlevideo.com. Idempotent."""
    global _patched
    if _patched:
        return True
    try:
        from pytubefix import request as _ptf_req
    except Exception as e:
        log.warning("pytubefix unavailable, cookie patch skipped: %s", e)
        return False

    original = _ptf_req._execute_request

    if getattr(original, "_yt_cookies_patched", False):
        _patched = True
        return True

    def _patched_execute(url, method=None, headers=None, data=None, timeout=None):
        merged = dict(headers) if headers else {}
        if isinstance(url, str):
            try:
                host = (urlparse(url).hostname or "").lower()
            except Exception:
                host = ""
            if any(frag.strip(".") in host for frag in _YT_HOST_FRAGMENTS):
                header = load_cookies_header()
                if header:
                    # Don't clobber an explicit Cookie passed by caller.
                    if "Cookie" not in merged and "cookie" not in merged:
                        merged["Cookie"] = header
        # Forward only kwargs that the original accepted.
        if timeout is None:
            return original(url, method=method, headers=merged, data=data)
        return original(url, method=method, headers=merged, data=data, timeout=timeout)

    _patched_execute._yt_cookies_patched = True  # type: ignore[attr-defined]
    _ptf_req._execute_request = _patched_execute
    _patched = True
    log.info("Installed pytubefix cookie injection patch for youtube.com / googlevideo.com.")
    return True
