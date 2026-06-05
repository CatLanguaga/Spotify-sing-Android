"""Edge guards on admin / config endpoints.

Two cheap policies that run before any route logic:

1. Body size cap (always-on). Reject Content-Length > ADMIN_BODY_MAX_BYTES
   on `/admin/*` and `/config`. Pydantic limits exist but a 10 MB JSON blob
   would still consume CPU before parser rejection.

2. UA heuristic (opt-in via ADMIN_BLOCK_GENERIC_UA=1). Reject empty UA or
   automation tools (curl, python-requests, wget, ...) unless they carry
   a custom marker header `X-Admin-Client`. Soft heuristic — useful as a
   second-layer filter on a public deploy, not a security boundary.

Failures respect ADMIN_STEALTH (404 instead of 403/413).
"""
from __future__ import annotations

import os
from typing import Iterable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

_PROTECTED_PREFIXES: tuple[str, ...] = ("/api/admin/", "/api/config")
_DEFAULT_BODY_MAX = 8 * 1024  # 8 KB


def _stealth() -> bool:
    return os.environ.get("ADMIN_STEALTH", "").lower() in {"1", "true", "yes"}


def _block_generic_ua() -> bool:
    return os.environ.get("ADMIN_BLOCK_GENERIC_UA", "").lower() in {"1", "true", "yes"}


def _body_max() -> int:
    try:
        return max(1024, int(os.environ.get("ADMIN_BODY_MAX_BYTES", _DEFAULT_BODY_MAX)))
    except ValueError:
        return _DEFAULT_BODY_MAX


_BLOCKED_UA_TOKENS: tuple[str, ...] = (
    "curl/",
    "wget/",
    "python-requests/",
    "python-urllib/",
    "go-http-client/",
    "httpie/",
    "scrapy/",
    "libwww-perl/",
)


def _is_protected(path: str) -> bool:
    return any(path.startswith(p) for p in _PROTECTED_PREFIXES)


def _stealth_or(status: int, detail: str) -> Response:
    if _stealth():
        return JSONResponse({"detail": "Not Found"}, status_code=404)
    return JSONResponse({"detail": detail}, status_code=status)


def _ua_blocked(ua: str) -> bool:
    if not ua:
        return True  # empty UA — almost always automation
    ua_l = ua.lower()
    return any(tok in ua_l for tok in _BLOCKED_UA_TOKENS)


class AdminGuardMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not _is_protected(path):
            return await call_next(request)

        # 1. Body size cap (cheap: header-only check, no read)
        cl = request.headers.get("content-length")
        if cl:
            try:
                if int(cl) > _body_max():
                    return _stealth_or(413, "Payload too large.")
            except ValueError:
                return _stealth_or(400, "Invalid Content-Length.")

        # 2. Optional UA heuristic — only applies when explicitly enabled
        if _block_generic_ua():
            ua = request.headers.get("user-agent", "")
            marker = request.headers.get("x-admin-client")
            if _ua_blocked(ua) and not marker:
                return _stealth_or(403, "Forbidden.")

        return await call_next(request)
