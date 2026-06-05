"""Signed session tokens + server-side revocation.

Token format (itsdangerous TimestampSigner):
    "{user_id}.{jti}" → signed → opaque string in cookie

Each issued token has a row in admin_sessions(jti). Validation requires
both signature OK and DB row present, not revoked, not expired,
not idle past ADMIN_IDLE_TIMEOUT_SECONDS.
"""
from __future__ import annotations

import hashlib
import logging
import os
import secrets
import time
from dataclasses import dataclass
from typing import Optional

from itsdangerous import BadSignature, SignatureExpired, TimestampSigner

from .db import connect
from .secret import load_or_create_secret

log = logging.getLogger(__name__)

SESSION_TTL_SECONDS = int(os.environ.get("ADMIN_SESSION_TTL_SECONDS", str(2 * 60 * 60)))     # 2h
IDLE_TIMEOUT_SECONDS = int(os.environ.get("ADMIN_IDLE_TIMEOUT_SECONDS", str(30 * 60)))       # 30m

_SALT = "admin-session-v1"
_signer: Optional[TimestampSigner] = None


def _get_signer() -> TimestampSigner:
    global _signer
    if _signer is None:
        _signer = TimestampSigner(load_or_create_secret(), salt=_SALT)
    return _signer


def reload_signer() -> None:
    """Call after rotate_secret()."""
    global _signer
    _signer = None


# ── Hashing client metadata (for forensic correlation, not identity) ────
def _hash_meta(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    pepper = os.environ.get("ADMIN_META_PEPPER", "spotify-sing-default-pepper")
    h = hashlib.sha256((value + pepper).encode("utf-8")).hexdigest()
    return h[:16]


@dataclass
class IssuedSession:
    token: str  # what goes in the cookie
    jti: str
    expires_at: int


def issue(user_id: int, *, ip: Optional[str] = None, user_agent: Optional[str] = None) -> IssuedSession:
    now = int(time.time())
    jti = secrets.token_urlsafe(16)
    expires_at = now + SESSION_TTL_SECONDS

    with connect() as conn:
        conn.execute(
            """INSERT INTO admin_sessions
               (jti, user_id, created_at, expires_at, last_seen_at, ip_hash, ua_hash)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (jti, user_id, now, expires_at, now, _hash_meta(ip), _hash_meta(user_agent)),
        )

    payload = f"{user_id}.{jti}"
    token = _get_signer().sign(payload.encode("utf-8")).decode("ascii")
    return IssuedSession(token=token, jti=jti, expires_at=expires_at)


@dataclass
class ValidSession:
    user_id: int
    jti: str
    expires_at: int
    refreshed: bool  # True if we extended expires_at on this validation


def validate(token: Optional[str]) -> Optional[ValidSession]:
    if not token:
        return None
    try:
        # max_age == TTL — any session whose signature timestamp is older is dead.
        raw = _get_signer().unsign(token.encode("ascii"), max_age=SESSION_TTL_SECONDS)
    except SignatureExpired:
        return None
    except BadSignature:
        return None
    except Exception:
        return None

    try:
        user_id_s, jti = raw.decode("utf-8").split(".", 1)
        user_id = int(user_id_s)
    except (ValueError, UnicodeDecodeError):
        return None

    now = int(time.time())
    with connect() as conn:
        row = conn.execute(
            """SELECT user_id, expires_at, last_seen_at, revoked_at
               FROM admin_sessions WHERE jti = ?""",
            (jti,),
        ).fetchone()
        if not row:
            return None
        if row["revoked_at"] is not None:
            return None
        if row["user_id"] != user_id:
            return None
        if row["expires_at"] < now:
            return None
        if now - row["last_seen_at"] > IDLE_TIMEOUT_SECONDS:
            # Idle past threshold → revoke
            conn.execute(
                "UPDATE admin_sessions SET revoked_at = ? WHERE jti = ?",
                (now, jti),
            )
            return None

        # Sliding refresh: bump last_seen + extend expiry up to original TTL ceiling
        new_expires = now + SESSION_TTL_SECONDS
        conn.execute(
            "UPDATE admin_sessions SET last_seen_at = ?, expires_at = ? WHERE jti = ?",
            (now, new_expires, jti),
        )

    return ValidSession(user_id=user_id, jti=jti, expires_at=new_expires, refreshed=True)


def revoke(jti: str) -> None:
    now = int(time.time())
    with connect() as conn:
        conn.execute(
            "UPDATE admin_sessions SET revoked_at = ? WHERE jti = ? AND revoked_at IS NULL",
            (now, jti),
        )


def revoke_all_for_user(user_id: int) -> int:
    now = int(time.time())
    with connect() as conn:
        cur = conn.execute(
            "UPDATE admin_sessions SET revoked_at = ? WHERE user_id = ? AND revoked_at IS NULL",
            (now, user_id),
        )
        return cur.rowcount


def purge_expired(older_than_seconds: int = 7 * 24 * 3600) -> int:
    """Housekeeping: drop rows that have been dead for a while."""
    cutoff = int(time.time()) - older_than_seconds
    with connect() as conn:
        cur = conn.execute(
            "DELETE FROM admin_sessions WHERE expires_at < ? OR (revoked_at IS NOT NULL AND revoked_at < ?)",
            (cutoff, cutoff),
        )
        return cur.rowcount
