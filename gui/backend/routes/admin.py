"""Admin auth routes.

Phase 11 hardening rounds 1-2:
- DB-backed user (Argon2id) instead of single ADMIN_PASSWORD env.
- Signed sessions with server-side revocation (itsdangerous + admin_sessions).
- IP rate-limit (slowapi) + per-user progressive lockout.
- Uniform 401 + constant-time delay to mitigate user enumeration / timing.
- Append-only audit log + JSON stdout mirror.
- Double-submit CSRF on every authenticated mutating endpoint (except login).
- ADMIN_PASSWORD env is honored only as a one-shot seed when DB has no users.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field

from gui.backend.admin import audit as admin_audit
from gui.backend.admin import csrf as admin_csrf
from gui.backend.admin import sessions as admin_sessions
from gui.backend.admin import users as admin_users
from gui.backend.admin import yt_cookies as admin_yt_cookies
from gui.backend.admin.ratelimit import LOGIN_PER_IP, limiter

YT_COOKIES_PER_HOUR = "5/hour"

# Pre-computed dummy hash so missing-user path costs ~ the same as real verify.
_DUMMY_HASH = admin_users._hash("dummy-password-for-timing-equalization")  # type: ignore[attr-defined]

log = logging.getLogger(__name__)
router = APIRouter(tags=["admin"])

_COOKIE_BASE = "spotify_sing_admin"
_LOGIN_TIMING_DELAY_MS = 200
_STEALTH_DETAIL = "Not Found"


def _stealth_enabled() -> bool:
    return os.environ.get("ADMIN_STEALTH", "").lower() in {"1", "true", "yes"}


def _auth_error(detail: str, *, status: int = 401) -> HTTPException:
    """Return 404 instead of the real status when stealth is on, so the
    admin surface is indistinguishable from a non-existent route."""
    if _stealth_enabled():
        return HTTPException(404, _STEALTH_DETAIL)
    return HTTPException(status, detail)


def _cookie_secure() -> bool:
    return os.environ.get("ADMIN_COOKIE_SECURE", "").lower() in {"1", "true", "yes"}


def _cookie_name() -> str:
    return f"__Host-{_COOKIE_BASE}" if _cookie_secure() else _COOKIE_BASE


def _cookie_samesite() -> str:
    return "strict"


def _constant_time_delay(start: float) -> None:
    elapsed_ms = (time.monotonic() - start) * 1000
    remaining = (_LOGIN_TIMING_DELAY_MS - elapsed_ms) / 1000
    if remaining > 0:
        time.sleep(remaining)


def _client_ip(request: Request) -> Optional[str]:
    # Honor proxy-set X-Forwarded-For when present (first hop).
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else None


# ── Models ──────────────────────────────────────────────────────────────
class AdminLoginRequest(BaseModel):
    model_config = {"extra": "forbid"}
    password: str = Field(..., min_length=1, max_length=512)
    username: Optional[str] = Field(default=None, max_length=64)


# ── Dependencies ────────────────────────────────────────────────────────
def _read_cookie(request: Request) -> Optional[str]:
    return (
        request.cookies.get(_cookie_name())
        or request.cookies.get(_COOKIE_BASE)
        or request.cookies.get(f"__Host-{_COOKIE_BASE}")
    )


def _current_session(request: Request) -> Optional[admin_sessions.ValidSession]:
    token = _read_cookie(request)
    return admin_sessions.validate(token)


def require_admin(request: Request) -> admin_sessions.ValidSession:
    """FastAPI dependency. Preserves old import path & signature."""
    sess = _current_session(request)
    if sess is None:
        raise _auth_error("Admin login required.", status=401)
    return sess


def require_admin_csrf(request: Request) -> admin_sessions.ValidSession:
    """Authenticated mutating endpoints — both auth + CSRF gate."""
    sess = require_admin(request)
    try:
        admin_csrf.require_csrf(request)
    except HTTPException as exc:
        # Log CSRF rejection separately from auth failures.
        admin_audit.record(
            "csrf_fail",
            result="blocked",
            user_id=sess.user_id,
            target=str(request.url.path),
            ip=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
        # Mask CSRF failure as 404 under stealth so probes can't enumerate
        # the existence of mutating admin endpoints either.
        if _stealth_enabled():
            raise HTTPException(404, _STEALTH_DETAIL) from exc
        raise
    return sess


# ── Cookie helpers ──────────────────────────────────────────────────────
def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        _cookie_name(),
        token,
        max_age=admin_sessions.SESSION_TTL_SECONDS,
        expires=admin_sessions.SESSION_TTL_SECONDS,
        httponly=True,
        secure=_cookie_secure(),
        samesite=_cookie_samesite(),
        path="/",
    )


def _clear_all_cookies(response: Response) -> None:
    for name in (_cookie_name(), _COOKIE_BASE, f"__Host-{_COOKIE_BASE}"):
        response.delete_cookie(name, path="/")
    admin_csrf.clear(response)


# ── Routes ──────────────────────────────────────────────────────────────
@router.get("/admin/session")
def admin_session(request: Request, response: Response):
    sess = _current_session(request)
    payload = {
        "authenticated": sess is not None,
        "provisioned": admin_users.count_users() > 0,
    }
    if sess is not None:
        # Ensure the CSRF cookie exists for already-authenticated clients
        # (covers upgrades from round 1 where no CSRF cookie was issued).
        if admin_csrf._read_cookie(request) is None:  # type: ignore[attr-defined]
            admin_csrf.issue(response)
    return payload


@router.post("/admin/login")
@limiter.limit(LOGIN_PER_IP)
def admin_login(request: Request, body: AdminLoginRequest, response: Response):
    started = time.monotonic()
    username = (body.username or "admin").strip().lower()
    ip = _client_ip(request)
    ua = request.headers.get("user-agent")
    try:
        request.state.login_username = username
    except Exception:
        pass

    if admin_users.count_users() == 0:
        _constant_time_delay(started)
        admin_audit.record("login_fail", result="blocked", username=username,
                           target="not_provisioned", ip=ip, user_agent=ua)
        raise HTTPException(
            503,
            "Admin not provisioned. Set ADMIN_PASSWORD env or use the admin_cli to create a user.",
        )

    user = admin_users.get_by_username(username)
    if user is None:
        admin_users._verify(_DUMMY_HASH, body.password)  # type: ignore[attr-defined]
        _constant_time_delay(started)
        admin_audit.record("login_fail", result="fail", username=username,
                           target="unknown_user", ip=ip, user_agent=ua)
        raise HTTPException(401, "Invalid credentials.")

    if not user.is_active:
        _constant_time_delay(started)
        admin_audit.record("login_fail", result="fail", user_id=user.id, username=username,
                           target="inactive", ip=ip, user_agent=ua)
        raise HTTPException(401, "Invalid credentials.")

    if user.is_locked():
        _constant_time_delay(started)
        retry_after = max(1, (user.locked_until or 0) - int(time.time())) if user.locked_until else None
        admin_audit.record("login_blocked", result="blocked", user_id=user.id, username=username,
                           target="locked", ip=ip, user_agent=ua,
                           meta={"locked_until": user.locked_until})
        headers = {"Retry-After": str(retry_after)} if retry_after else None
        raise HTTPException(
            status_code=423,
            detail="Account temporarily locked. Try again later or contact an administrator.",
            headers=headers,
        )

    if not admin_users.verify_password(user, body.password):
        new_count, locked_until = admin_users.record_failure(user)
        _constant_time_delay(started)
        admin_audit.record("login_fail", result="fail", user_id=user.id, username=username,
                           target="wrong_password", ip=ip, user_agent=ua,
                           meta={"failed_attempts": new_count})
        if locked_until is not None:
            admin_audit.record("lockout", result="info", user_id=user.id, username=username,
                               ip=ip, user_agent=ua,
                               meta={"locked_until": locked_until, "after_attempts": new_count})
        raise HTTPException(401, "Invalid credentials.")

    admin_users.record_success(user, body.password)
    issued = admin_sessions.issue(user.id, ip=ip, user_agent=ua)
    _set_session_cookie(response, issued.token)
    admin_csrf.issue(response)
    admin_audit.record("login_ok", result="ok", user_id=user.id, username=username,
                       ip=ip, user_agent=ua, meta={"jti": issued.jti})
    _constant_time_delay(started)
    return {"authenticated": True}


@router.post("/admin/logout")
def admin_logout(
    request: Request,
    response: Response,
    sess: admin_sessions.ValidSession = Depends(require_admin_csrf),
):
    admin_sessions.revoke(sess.jti)
    admin_audit.record("logout", result="ok", user_id=sess.user_id,
                       ip=_client_ip(request), user_agent=request.headers.get("user-agent"),
                       meta={"jti": sess.jti})
    _clear_all_cookies(response)
    return {"authenticated": False}


@router.post("/admin/logout-all")
def admin_logout_all(
    request: Request,
    response: Response,
    sess: admin_sessions.ValidSession = Depends(require_admin_csrf),
):
    n = admin_sessions.revoke_all_for_user(sess.user_id)
    admin_audit.record("logout_all", result="ok", user_id=sess.user_id,
                       ip=_client_ip(request), user_agent=request.headers.get("user-agent"),
                       meta={"revoked": n})
    _clear_all_cookies(response)
    return {"authenticated": False, "revoked": n}


# ── YouTube cookies (11.10) ─────────────────────────────────────────────
class YtCookiesUploadRequest(BaseModel):
    model_config = {"extra": "forbid"}
    content: str = Field(..., min_length=10, max_length=200 * 1024,
                         description="Netscape-format cookies.txt content.")
    validate_live: bool = Field(default=False,
                                description="If true, hit youtube.com to confirm session is alive.")


@router.get("/admin/youtube-cookies/status")
def admin_yt_cookies_status(
    request: Request,
    sess: admin_sessions.ValidSession = Depends(require_admin),
):
    meta = admin_yt_cookies.read_meta()
    return {
        "present": admin_yt_cookies.is_present(),
        "uploaded_at": meta.get("uploaded_at"),
        "last_validated_at": meta.get("last_validated_at"),
        "last_status": meta.get("last_status"),
    }


@router.post("/admin/youtube-cookies")
@limiter.limit(YT_COOKIES_PER_HOUR)
def admin_yt_cookies_upload(
    request: Request,
    body: YtCookiesUploadRequest,
    sess: admin_sessions.ValidSession = Depends(require_admin_csrf),
):
    ip = _client_ip(request)
    ua = request.headers.get("user-agent")
    try:
        meta = admin_yt_cookies.save_cookies(body.content)
    except admin_yt_cookies.CookiesError as e:
        admin_audit.record("youtube_cookies_upload", result="fail",
                           user_id=sess.user_id, ip=ip, user_agent=ua,
                           meta={"error": str(e)[:200]})
        raise HTTPException(400, str(e))
    except Exception as e:
        log.exception("Unexpected error saving YouTube cookies")
        admin_audit.record("youtube_cookies_upload", result="fail",
                           user_id=sess.user_id, ip=ip, user_agent=ua,
                           meta={"error": str(e)[:200]})
        raise HTTPException(500, "Failed to save cookies.")

    admin_yt_cookies.install_cookie_patch()

    if body.validate_live:
        ok, message = admin_yt_cookies.validate_against_youtube()
        admin_yt_cookies.record_validation_result(ok, message)
        meta = admin_yt_cookies.read_meta()
        admin_audit.record("youtube_cookies_upload", result="ok" if ok else "warn",
                           user_id=sess.user_id, ip=ip, user_agent=ua,
                           meta={"live_check": ok, "message": message[:200]})
    else:
        admin_audit.record("youtube_cookies_upload", result="ok",
                           user_id=sess.user_id, ip=ip, user_agent=ua)

    return {"ok": True, **meta}


@router.delete("/admin/youtube-cookies")
def admin_yt_cookies_delete(
    request: Request,
    sess: admin_sessions.ValidSession = Depends(require_admin_csrf),
):
    removed = admin_yt_cookies.delete_cookies()
    admin_audit.record("youtube_cookies_delete", result="ok",
                       user_id=sess.user_id,
                       ip=_client_ip(request),
                       user_agent=request.headers.get("user-agent"),
                       meta={"removed": removed})
    return {"ok": True, "removed": removed}


# ── Audit query ─────────────────────────────────────────────────────────
@router.get("/admin/audit")
def admin_audit_list(
    request: Request,
    limit: int = Query(100, ge=1, le=1000),
    since: Optional[int] = Query(None, description="Unix epoch seconds (>=)"),
    action: Optional[str] = Query(None, max_length=64),
    user_id: Optional[int] = Query(None),
    sess: admin_sessions.ValidSession = Depends(require_admin),
):
    events = admin_audit.list_events(limit=limit, since_ts=since, action=action, user_id=user_id)
    admin_audit.record("audit_view", result="ok", user_id=sess.user_id,
                       ip=_client_ip(request), user_agent=request.headers.get("user-agent"),
                       meta={"limit": limit, "returned": len(events)})
    return {"events": events, "count": len(events)}
