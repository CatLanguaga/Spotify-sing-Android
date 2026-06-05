"""Admin audit log: append-only DB rows + JSON stdout mirror.

Designed for forensic correlation, not user identification:
    - IP and User-Agent stored as sha256(value + pepper)[:16]
    - Action vocabulary fixed (see ACTIONS) so dashboards can group
    - Result is "ok" | "fail" | "denied" | "blocked" | "info"
    - meta_json is small free-form JSON (≤ 2KB; truncated)

JSON stdout line schema:
    {"audit": True, "ts": <iso>, "action": "...", "result": "...", ...}
suitable for Coolify/Loki ingestion.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

from .db import connect

log = logging.getLogger("admin.audit")

# Canonical action vocabulary. Add new values here so consumers can rely on it.
ACTIONS: tuple[str, ...] = (
    "login_ok",
    "login_fail",
    "login_blocked",     # rate-limited / locked
    "lockout",
    "logout",
    "logout_all",
    "password_change",
    "totp_enable",
    "totp_disable",
    "session_revoke",
    "user_create",
    "user_delete",
    "user_lock",
    "user_unlock",
    "config_write",
    "csrf_fail",
    "audit_view",
    "youtube_cookies_upload",
    "youtube_cookies_delete",
    "youtube_cookies_invalid",
)

_META_MAX_BYTES = 2048


def _hash_meta(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    pepper = os.environ.get("ADMIN_META_PEPPER", "spotify-sing-default-pepper")
    return hashlib.sha256((value + pepper).encode("utf-8")).hexdigest()[:16]


def _serialize_meta(meta: Optional[dict[str, Any]]) -> Optional[str]:
    if not meta:
        return None
    try:
        blob = json.dumps(meta, default=str, separators=(",", ":"), ensure_ascii=False)
    except Exception:
        return None
    if len(blob) > _META_MAX_BYTES:
        blob = blob[: _META_MAX_BYTES - 1] + "…"
    return blob


def record(
    action: str,
    *,
    result: str = "ok",
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    target: Optional[str] = None,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    meta: Optional[dict[str, Any]] = None,
) -> None:
    """Append an audit row + emit a JSON log line. Never raises."""
    now = int(time.time())
    ip_h = _hash_meta(ip)
    ua_h = _hash_meta(user_agent)
    meta_blob = _serialize_meta(meta)

    try:
        with connect() as conn:
            conn.execute(
                """INSERT INTO admin_audit
                   (ts, user_id, username, ip_hash, ua_hash, action, target, result, meta_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (now, user_id, username, ip_h, ua_h, action, target, result, meta_blob),
            )
    except Exception as e:
        log.warning("Audit DB write failed action=%s: %s", action, e)

    try:
        log.info(
            json.dumps(
                {
                    "audit": True,
                    "ts": datetime.fromtimestamp(now, tz=timezone.utc).isoformat(),
                    "action": action,
                    "result": result,
                    "user_id": user_id,
                    "username": username,
                    "target": target,
                    "ip_hash": ip_h,
                    "ua_hash": ua_h,
                    "meta": meta if meta else None,
                },
                default=str,
                ensure_ascii=False,
            )
        )
    except Exception:
        pass


def list_events(
    *,
    limit: int = 100,
    since_ts: Optional[int] = None,
    action: Optional[str] = None,
    user_id: Optional[int] = None,
) -> list[dict[str, Any]]:
    limit = max(1, min(limit, 1000))
    clauses: list[str] = []
    params: list[Any] = []
    if since_ts is not None:
        clauses.append("ts >= ?")
        params.append(int(since_ts))
    if action:
        clauses.append("action = ?")
        params.append(action)
    if user_id is not None:
        clauses.append("user_id = ?")
        params.append(int(user_id))
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"SELECT * FROM admin_audit{where} ORDER BY id DESC LIMIT ?"
    params.append(limit)

    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()

    out: list[dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                "id": r["id"],
                "ts": r["ts"],
                "ts_iso": datetime.fromtimestamp(r["ts"], tz=timezone.utc).isoformat(),
                "user_id": r["user_id"],
                "username": r["username"],
                "ip_hash": r["ip_hash"],
                "ua_hash": r["ua_hash"],
                "action": r["action"],
                "target": r["target"],
                "result": r["result"],
                "meta": json.loads(r["meta_json"]) if r["meta_json"] else None,
            }
        )
    return out
