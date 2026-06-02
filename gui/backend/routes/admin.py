import base64
import hashlib
import hmac
import os
import time
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel

router = APIRouter(tags=["admin"])

_COOKIE_NAME = "spotify_sing_admin"
_SESSION_TTL_SECONDS = int(os.environ.get("ADMIN_SESSION_TTL_SECONDS", "86400"))


class AdminLoginRequest(BaseModel):
    password: str


def _admin_password() -> str:
    return os.environ.get("ADMIN_PASSWORD") or os.environ.get("SPOTIFY_ADMIN_PASSWORD") or "admin"


def _session_secret() -> bytes:
    secret = (
        os.environ.get("ADMIN_SESSION_SECRET")
        or os.environ.get("SPOTIFY_ADMIN_SESSION_SECRET")
        or _admin_password()
    )
    return secret.encode("utf-8")


def _sign(payload: str) -> str:
    return hmac.new(_session_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def _encode_session(expires_at: int) -> str:
    payload = f"admin:{expires_at}"
    token = f"{payload}:{_sign(payload)}"
    return base64.urlsafe_b64encode(token.encode("utf-8")).decode("ascii")


def _decode_session(value: str | None) -> bool:
    if not value:
        return False
    try:
        token = base64.urlsafe_b64decode(value.encode("ascii")).decode("utf-8")
        user, expires_raw, signature = token.rsplit(":", 2)
        payload = f"{user}:{expires_raw}"
        if user != "admin":
            return False
        if not hmac.compare_digest(signature, _sign(payload)):
            return False
        return int(expires_raw) >= int(time.time())
    except Exception:
        return False


def _cookie_secure() -> bool:
    return os.environ.get("ADMIN_COOKIE_SECURE", "").lower() in {"1", "true", "yes"}


def require_admin(
    admin_cookie: Annotated[str | None, Cookie(alias=_COOKIE_NAME)] = None,
) -> None:
    if not _decode_session(admin_cookie):
        raise HTTPException(401, "Admin login required.")


@router.get("/admin/session")
def admin_session(admin_cookie: Annotated[str | None, Cookie(alias=_COOKIE_NAME)] = None):
    return {
        "authenticated": _decode_session(admin_cookie),
        "default_password": not (
            os.environ.get("ADMIN_PASSWORD") or os.environ.get("SPOTIFY_ADMIN_PASSWORD")
        ),
    }


@router.post("/admin/login")
def admin_login(body: AdminLoginRequest, response: Response):
    if not hmac.compare_digest(body.password, _admin_password()):
        raise HTTPException(401, "Invalid admin password.")

    expires_at = int(time.time()) + _SESSION_TTL_SECONDS
    response.set_cookie(
        _COOKIE_NAME,
        _encode_session(expires_at),
        max_age=_SESSION_TTL_SECONDS,
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",
        path="/",
    )
    return {"authenticated": True}


@router.post("/admin/logout")
def admin_logout(response: Response, _admin: None = Depends(require_admin)):
    response.delete_cookie(_COOKIE_NAME, path="/")
    return {"authenticated": False}
