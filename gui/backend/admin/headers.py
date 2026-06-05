"""Security headers + optional HTTPS redirect.

Always-on (cheap, no break risk):
    X-Content-Type-Options: nosniff
    X-Frame-Options:        DENY
    Referrer-Policy:        strict-origin-when-cross-origin
    Permissions-Policy:     geolocation=(), microphone=(), camera=()
    Server:                 (stripped / replaced with generic value)

Opt-in via SECURITY_HEADERS_STRICT=1 (production):
    Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
    Content-Security-Policy:   strict policy (see below)

Opt-in via FORCE_HTTPS=1:
    Redirect any plain-HTTP request to https://. Honors X-Forwarded-Proto so
    it works behind Coolify's Traefik proxy without double-redirecting.
"""
from __future__ import annotations

import os
from typing import Iterable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

_STATIC_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}

_HSTS = "max-age=63072000; includeSubDomains; preload"

# Note: 'unsafe-inline' on style-src is kept because Vite/React injects small
# inline styles. img-src includes Spotify CDN + data: for embedded SVG.
_CSP = (
    "default-src 'self'; "
    "img-src 'self' https://i.scdn.co data:; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "connect-src 'self'; "
    "frame-ancestors 'none'"
)

_SERVER_VALUE = os.environ.get("SECURITY_SERVER_HEADER", "nginx")


def _strict_enabled() -> bool:
    return os.environ.get("SECURITY_HEADERS_STRICT", "").lower() in {"1", "true", "yes"}


def _force_https() -> bool:
    return os.environ.get("FORCE_HTTPS", "").lower() in {"1", "true", "yes"}


def _request_is_https(request: Request) -> bool:
    if request.url.scheme == "https":
        return True
    # Trust the proxy header (Coolify/Traefik sets it). Behind something else,
    # operators should set the proxy to inject this header too.
    fwd = request.headers.get("x-forwarded-proto", "").lower()
    return fwd.split(",")[0].strip() == "https"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if _force_https() and request.method in {"GET", "HEAD"} and not _request_is_https(request):
            # Only redirect safe methods — POST under wrong scheme is rejected upstream.
            target = request.url.replace(scheme="https")
            return RedirectResponse(url=str(target), status_code=308)

        if _force_https() and not _request_is_https(request):
            return Response("HTTPS required.", status_code=400)

        response: Response = await call_next(request)

        for k, v in _STATIC_HEADERS.items():
            response.headers.setdefault(k, v)

        if _strict_enabled():
            response.headers.setdefault("Strict-Transport-Security", _HSTS)
            response.headers.setdefault("Content-Security-Policy", _CSP)

        # Overwrite Server (uvicorn leaks version otherwise).
        response.headers["Server"] = _SERVER_VALUE
        return response
