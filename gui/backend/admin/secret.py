"""Session-signing secret loader.

Priority:
1. ADMIN_SESSION_SECRET env (must be >= 32 bytes after utf-8 encoding).
2. data/.session_secret file (auto-generated on first start, perms 0600).

Rotation: delete the file (or change the env) and restart — all existing
sessions become invalid because the signature no longer verifies.
"""
from __future__ import annotations

import logging
import os
import secrets
import stat
from pathlib import Path

from .db import DB_PATH

log = logging.getLogger(__name__)

_SECRET_FILE = DB_PATH.parent / ".session_secret"
_MIN_BYTES = 32


def load_or_create_secret() -> bytes:
    env_val = os.environ.get("ADMIN_SESSION_SECRET")
    if env_val:
        raw = env_val.encode("utf-8")
        if len(raw) < _MIN_BYTES:
            raise RuntimeError(
                f"ADMIN_SESSION_SECRET must be >= {_MIN_BYTES} bytes; got {len(raw)}."
            )
        return raw

    if _SECRET_FILE.exists():
        data = _SECRET_FILE.read_bytes().strip()
        if len(data) >= _MIN_BYTES:
            return data
        log.warning("Session secret file too short, regenerating: %s", _SECRET_FILE)

    _SECRET_FILE.parent.mkdir(parents=True, exist_ok=True)
    new_secret = secrets.token_bytes(48)
    _SECRET_FILE.write_bytes(new_secret)
    try:
        os.chmod(_SECRET_FILE, stat.S_IRUSR | stat.S_IWUSR)  # 0600 (no-op on Windows)
    except OSError:
        pass
    log.info("Generated new admin session secret at %s", _SECRET_FILE)
    return new_secret


def rotate_secret() -> bytes:
    """Force generate a new secret. Invalidates all existing sessions."""
    if _SECRET_FILE.exists():
        _SECRET_FILE.unlink()
    return load_or_create_secret()
