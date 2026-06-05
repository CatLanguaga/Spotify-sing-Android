"""SQLite connection + schema for admin auth."""
from __future__ import annotations

import os
import sqlite3
import threading
from pathlib import Path

_ROOT = Path(os.environ.get("SPOTIFY_SYNC_ROOT", Path(__file__).parent.parent.parent.parent))
_DEFAULT_DB = _ROOT / "data" / "admin.sqlite3"

DB_PATH = Path(os.environ.get("ADMIN_DB_PATH", _DEFAULT_DB))

_lock = threading.Lock()
_initialized = False


_SCHEMA = """
CREATE TABLE IF NOT EXISTS admin_users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash   TEXT NOT NULL,
    password_algo   TEXT NOT NULL,
    created_at      INTEGER NOT NULL,
    updated_at      INTEGER NOT NULL,
    last_login_at   INTEGER,
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until    INTEGER,
    totp_secret     TEXT,
    is_active       INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS admin_sessions (
    jti          TEXT PRIMARY KEY,
    user_id      INTEGER NOT NULL,
    created_at   INTEGER NOT NULL,
    expires_at   INTEGER NOT NULL,
    last_seen_at INTEGER NOT NULL,
    revoked_at   INTEGER,
    ip_hash      TEXT,
    ua_hash      TEXT,
    FOREIGN KEY (user_id) REFERENCES admin_users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON admin_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON admin_sessions(expires_at);

CREATE TABLE IF NOT EXISTS admin_audit (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    ts        INTEGER NOT NULL,
    user_id   INTEGER,
    username  TEXT,
    ip_hash   TEXT,
    ua_hash   TEXT,
    action    TEXT NOT NULL,
    target    TEXT,
    result    TEXT NOT NULL,
    meta_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_audit_ts ON admin_audit(ts);
CREATE INDEX IF NOT EXISTS idx_audit_action ON admin_audit(action);
CREATE INDEX IF NOT EXISTS idx_audit_user ON admin_audit(user_id);
"""


def connect() -> sqlite3.Connection:
    """Open a connection. Each caller closes it. Schema lazily ensured."""
    _ensure_initialized()
    conn = sqlite3.connect(DB_PATH, isolation_level=None)  # autocommit
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def _ensure_initialized() -> None:
    global _initialized
    if _initialized:
        return
    with _lock:
        if _initialized:
            return
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(DB_PATH, isolation_level=None)
        try:
            conn.executescript(_SCHEMA)
        finally:
            conn.close()
        _initialized = True


def reset_for_tests() -> None:
    """Clear singleton flag; tests can point ADMIN_DB_PATH elsewhere."""
    global _initialized
    _initialized = False
