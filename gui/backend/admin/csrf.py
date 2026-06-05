"""Double-submit cookie CSRF for admin mutating endpoints.

Flow:
    1. /admin/login (any successful auth) sets cookie `spotify_sing_csrf`
       (NOT httponly — JS must read it to echo via header).
    2. Mutating requests (POST/PUT/PATCH/DELETE) must send the same value
       in the `X-CSRF-Token` header. Constant-time compare with the cookie.

Login itself is exempt: it has no session cookie yet, and rate-limit +
lockout already protect it. CSRF only matters for *authenticated* state
changes from a victim's browser.
"""
from __future__ import annotations

import hmac
import os
import secrets
from typing import Optional

from fastapi import HTTPException, Request, Response

_CSRF_COOKIE_BASE = "spotify_sing_csrf"
_CSRF_HEADER = "X-CSRF-Token"
_PROTECTED_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _cookie_secure() -> bool:
    return os.environ.get("ADMIN_COOKIE_SECURE", "").lower() in {"1", "true", "yes"}


def _cookie_name() -> str:
    # Match the session cookie's __Host- behavior so they share the same flag toggle.
    return f"__Host-{_CSRF_COOKIE_BASE}" if _cookie_secure() else _CSRF_COOKIE_BASE


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def issue(response: Response, *, token: Optional[str] = None) -> str:
    """Attach (or rotate) the CSRF cookie. Returns the token in case the
    caller wants to also embed it in a response body."""
    value = token or generate_token()
    response.set_cookie(
        _cookie_name(),
        value,
        max_age=int(os.environ.get("ADMIN_SESSION_TTL_SECONDS", str(2 * 60 * 60))),
        httponly=False,  # JS must read it for the double-submit
        secure=_cookie_secure(),
        samesite="strict",
        path="/",
    )
    return value


def clear(response: Response) -> None:
    response.delete_cookie(_cookie_name(), path="/")
    response.delete_cookie(_CSRF_COOKIE_BASE, path="/")
    response.delete_cookie(f"__Host-{_CSRF_COOKIE_BASE}", path="/")


def _read_cookie(request: Request) -> Optional[str]:
    return (
        request.cookies.get(_cookie_name())
        or request.cookies.get(_CSRF_COOKIE_BASE)
        or request.cookies.get(f"__Host-{_CSRF_COOKIE_BASE}")
    )


def require_csrf(request: Request) -> None:
    """FastAPI dep. Use on every mutating admin endpoint *except* login."""
    if request.method not in _PROTECTED_METHODS:
        return
    cookie = _read_cookie(request)
    header = request.headers.get(_CSRF_HEADER)
    if not cookie or not header:
        raise HTTPException(status_code=403, detail="CSRF token missing.")
    if not hmac.compare_digest(cookie, header):
        raise HTTPException(status_code=403, detail="CSRF token mismatch.")
