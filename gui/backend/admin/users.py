"""Admin user model: Argon2id hashing, lockout, attempt tracking.

Single-admin deployment for now, but model supports multiple users so the
CLI / future 2FA flow can extend without schema change.
"""
from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from typing import Optional

from .db import connect

log = logging.getLogger(__name__)

# ── Hashing backend selection ───────────────────────────────────────────
try:
    from argon2 import PasswordHasher
    from argon2.exceptions import VerifyMismatchError, InvalidHash

    _HASHER = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)
    _ALGO = "argon2id"

    def _hash(pw: str) -> str:
        return _HASHER.hash(pw)

    def _verify(stored: str, pw: str) -> bool:
        try:
            _HASHER.verify(stored, pw)
            return True
        except (VerifyMismatchError, InvalidHash, Exception):
            return False

    def _needs_rehash(stored: str) -> bool:
        try:
            return _HASHER.check_needs_rehash(stored)
        except Exception:
            return False

except ImportError:  # pragma: no cover - fallback only
    import bcrypt

    _ALGO = "bcrypt"

    def _hash(pw: str) -> str:
        return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("ascii")

    def _verify(stored: str, pw: str) -> bool:
        try:
            return bcrypt.checkpw(pw.encode("utf-8"), stored.encode("ascii"))
        except Exception:
            return False

    def _needs_rehash(stored: str) -> bool:
        return False


USERNAME_RE = re.compile(r"^[a-z0-9_.-]{3,32}$")
MIN_PASSWORD_LEN = 12

# Lazy-loaded set of lowercased blocked passwords. Bundled file ships ~120
# entries; ADMIN_PWNED_LIST env can point at a much larger corpus.
_PWNED_CACHE: Optional[set[str]] = None


def _load_pwned_list() -> set[str]:
    global _PWNED_CACHE
    if _PWNED_CACHE is not None:
        return _PWNED_CACHE
    import os
    from pathlib import Path
    candidates: list[Path] = []
    env_path = os.environ.get("ADMIN_PWNED_LIST")
    if env_path:
        candidates.append(Path(env_path))
    candidates.append(Path(__file__).parent / "data" / "common_passwords.txt")
    pwned: set[str] = set()
    for p in candidates:
        if not p.exists():
            continue
        try:
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    s = line.strip()
                    if not s or s.startswith("#"):
                        continue
                    pwned.add(s.lower())
            break
        except Exception as e:
            log.warning("Failed to load pwned list %s: %s", p, e)
    _PWNED_CACHE = pwned
    return pwned

# Progressive lockout thresholds — (consecutive_fails, lock_seconds)
_LOCKOUT_LEVELS = [
    (5, 15 * 60),
    (10, 60 * 60),
    (20, None),  # None = manual unlock required
]


class AdminError(Exception):
    pass


@dataclass
class AdminUser:
    id: int
    username: str
    password_hash: str
    password_algo: str
    created_at: int
    updated_at: int
    last_login_at: Optional[int]
    failed_attempts: int
    locked_until: Optional[int]
    is_active: bool

    @classmethod
    def _from_row(cls, row) -> "AdminUser":
        return cls(
            id=row["id"],
            username=row["username"],
            password_hash=row["password_hash"],
            password_algo=row["password_algo"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            last_login_at=row["last_login_at"],
            failed_attempts=row["failed_attempts"],
            locked_until=row["locked_until"],
            is_active=bool(row["is_active"]),
        )

    def is_locked(self, now: Optional[int] = None) -> bool:
        if self.locked_until is None:
            return False
        if self.locked_until == 0:
            return True  # 0 means manual unlock required
        return (now or int(time.time())) < self.locked_until


# ── Validation ──────────────────────────────────────────────────────────
def validate_username(username: str) -> str:
    norm = (username or "").strip().lower()
    if not USERNAME_RE.match(norm):
        raise AdminError("Username must match ^[a-z0-9_.-]{3,32}$.")
    return norm


def validate_password(pw: str) -> None:
    if not pw or len(pw) < MIN_PASSWORD_LEN:
        raise AdminError(f"Password must be at least {MIN_PASSWORD_LEN} characters.")
    classes = sum([
        any(c.islower() for c in pw),
        any(c.isupper() for c in pw),
        any(c.isdigit() for c in pw),
        any(not c.isalnum() for c in pw),
    ])
    if classes < 3:
        raise AdminError("Password must mix at least 3 character classes (lower/upper/digit/symbol).")
    if pw.lower() in _load_pwned_list():
        raise AdminError(
            "Password is on the common-passwords blocklist. Choose a less guessable one."
        )


# ── CRUD ────────────────────────────────────────────────────────────────
def count_users() -> int:
    with connect() as conn:
        cur = conn.execute("SELECT COUNT(*) FROM admin_users")
        return int(cur.fetchone()[0])


def list_users() -> list[AdminUser]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM admin_users ORDER BY id").fetchall()
        return [AdminUser._from_row(r) for r in rows]


def get_by_username(username: str) -> Optional[AdminUser]:
    norm = (username or "").strip().lower()
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM admin_users WHERE username = ? COLLATE NOCASE",
            (norm,),
        ).fetchone()
        return AdminUser._from_row(row) if row else None


def get_by_id(user_id: int) -> Optional[AdminUser]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM admin_users WHERE id = ?", (user_id,)).fetchone()
        return AdminUser._from_row(row) if row else None


def create_user(username: str, password: str, *, skip_strength_check: bool = False) -> AdminUser:
    norm = validate_username(username)
    if not skip_strength_check:
        validate_password(password)
    now = int(time.time())
    pw_hash = _hash(password)
    with connect() as conn:
        try:
            cur = conn.execute(
                """INSERT INTO admin_users
                   (username, password_hash, password_algo, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (norm, pw_hash, _ALGO, now, now),
            )
        except Exception as e:
            raise AdminError(f"Could not create user: {e}") from e
        user_id = cur.lastrowid
    log.info("Created admin user id=%s username=%s algo=%s", user_id, norm, _ALGO)
    user = get_by_id(user_id)
    assert user is not None
    return user


def set_password(username: str, password: str, *, skip_strength_check: bool = False) -> None:
    norm = validate_username(username)
    if not skip_strength_check:
        validate_password(password)
    pw_hash = _hash(password)
    now = int(time.time())
    with connect() as conn:
        cur = conn.execute(
            """UPDATE admin_users
               SET password_hash = ?, password_algo = ?, updated_at = ?,
                   failed_attempts = 0, locked_until = NULL
               WHERE username = ? COLLATE NOCASE""",
            (pw_hash, _ALGO, now, norm),
        )
        if cur.rowcount == 0:
            raise AdminError(f"User not found: {norm}")
    log.info("Reset password for username=%s", norm)


def lock_user(username: str, until_epoch: Optional[int] = 0) -> None:
    """until_epoch=0 means manual unlock required."""
    norm = validate_username(username)
    with connect() as conn:
        cur = conn.execute(
            "UPDATE admin_users SET locked_until = ?, updated_at = ? WHERE username = ? COLLATE NOCASE",
            (until_epoch, int(time.time()), norm),
        )
        if cur.rowcount == 0:
            raise AdminError(f"User not found: {norm}")
    log.warning("Locked admin user=%s until=%s", norm, until_epoch)


def unlock_user(username: str) -> None:
    norm = validate_username(username)
    with connect() as conn:
        cur = conn.execute(
            """UPDATE admin_users
               SET locked_until = NULL, failed_attempts = 0, updated_at = ?
               WHERE username = ? COLLATE NOCASE""",
            (int(time.time()), norm),
        )
        if cur.rowcount == 0:
            raise AdminError(f"User not found: {norm}")
    log.info("Unlocked admin user=%s", norm)


# ── Authentication outcome handling ─────────────────────────────────────
def verify_password(user: AdminUser, password: str) -> bool:
    return _verify(user.password_hash, password)


def record_success(user: AdminUser, password: str) -> None:
    now = int(time.time())
    new_hash: Optional[str] = None
    if _needs_rehash(user.password_hash):
        try:
            new_hash = _hash(password)
        except Exception as e:
            log.warning("Opportunistic rehash failed for user=%s: %s", user.username, e)
    with connect() as conn:
        if new_hash:
            conn.execute(
                """UPDATE admin_users
                   SET last_login_at = ?, failed_attempts = 0, locked_until = NULL,
                       updated_at = ?, password_hash = ?, password_algo = ?
                   WHERE id = ?""",
                (now, now, new_hash, _ALGO, user.id),
            )
        else:
            conn.execute(
                """UPDATE admin_users
                   SET last_login_at = ?, failed_attempts = 0, locked_until = NULL, updated_at = ?
                   WHERE id = ?""",
                (now, now, user.id),
            )


def record_failure(user: AdminUser) -> tuple[int, Optional[int]]:
    """Returns (new_failed_count, locked_until_epoch_or_None)."""
    now = int(time.time())
    new_count = user.failed_attempts + 1
    locked_until: Optional[int] = None
    # Find the highest threshold the count reached
    for threshold, duration in sorted(_LOCKOUT_LEVELS, reverse=True):
        if new_count >= threshold:
            if duration is None:
                locked_until = 0  # manual
            else:
                locked_until = now + duration
            break

    with connect() as conn:
        conn.execute(
            """UPDATE admin_users
               SET failed_attempts = ?, locked_until = ?, updated_at = ?
               WHERE id = ?""",
            (new_count, locked_until, now, user.id),
        )
    if locked_until is not None:
        log.warning(
            "Lockout triggered for user=%s after %d failed attempts (until=%s)",
            user.username, new_count, locked_until,
        )
    return new_count, locked_until
