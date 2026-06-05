"""Admin user CLI.

Usage:
    python -m gui.backend.admin_cli create-user <username>
    python -m gui.backend.admin_cli reset-password <username>
    python -m gui.backend.admin_cli lock <username>
    python -m gui.backend.admin_cli unlock <username>
    python -m gui.backend.admin_cli list-users
    python -m gui.backend.admin_cli rotate-secret      # invalidates all sessions
    python -m gui.backend.admin_cli revoke-sessions <username>

Passwords are always read from stdin (getpass) — never via argv, to keep
them out of process listings and shell history.
"""
from __future__ import annotations

import argparse
import getpass
import sys
import time
from datetime import datetime, timezone

# Allow `python -m gui.backend.admin_cli` from repo root.
import os
from pathlib import Path

_ROOT = Path(__file__).parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
os.environ.setdefault("SPOTIFY_SYNC_ROOT", str(_ROOT))

from gui.backend.admin import sessions as admin_sessions  # noqa: E402
from gui.backend.admin import users as admin_users  # noqa: E402
from gui.backend.admin.secret import rotate_secret  # noqa: E402


def _read_password_twice(prompt: str = "Password: ") -> str:
    p1 = getpass.getpass(prompt)
    p2 = getpass.getpass("Confirm: ")
    if p1 != p2:
        print("ERROR: passwords do not match", file=sys.stderr)
        sys.exit(2)
    return p1


def _fmt_ts(ts: int | None) -> str:
    if not ts:
        return "-"
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def cmd_create(args) -> int:
    try:
        admin_users.validate_username(args.username)
    except admin_users.AdminError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    if admin_users.get_by_username(args.username):
        print(f"ERROR: user already exists: {args.username}", file=sys.stderr)
        return 2
    pw = _read_password_twice()
    try:
        admin_users.validate_password(pw)
        user = admin_users.create_user(args.username, pw)
    except admin_users.AdminError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    print(f"Created user id={user.id} username={user.username}")
    return 0


def cmd_reset(args) -> int:
    user = admin_users.get_by_username(args.username)
    if user is None:
        print(f"ERROR: user not found: {args.username}", file=sys.stderr)
        return 2
    pw = _read_password_twice("New password: ")
    try:
        admin_users.set_password(args.username, pw)
    except admin_users.AdminError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    admin_sessions.revoke_all_for_user(user.id)
    print(f"Reset password for {args.username}; all sessions revoked.")
    return 0


def cmd_lock(args) -> int:
    try:
        admin_users.lock_user(args.username, until_epoch=0)
    except admin_users.AdminError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    user = admin_users.get_by_username(args.username)
    if user is not None:
        admin_sessions.revoke_all_for_user(user.id)
    print(f"Locked {args.username} (manual unlock required).")
    return 0


def cmd_unlock(args) -> int:
    try:
        admin_users.unlock_user(args.username)
    except admin_users.AdminError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    print(f"Unlocked {args.username}.")
    return 0


def cmd_list(_args) -> int:
    users = admin_users.list_users()
    if not users:
        print("(no admin users)")
        return 0
    print(f"{'ID':<4} {'USERNAME':<24} {'ACTIVE':<7} {'LOCKED':<8} {'FAILS':<6} {'LAST LOGIN'}")
    now = int(time.time())
    for u in users:
        locked = "yes" if u.is_locked(now) else "no"
        print(f"{u.id:<4} {u.username:<24} {'yes' if u.is_active else 'no':<7} "
              f"{locked:<8} {u.failed_attempts:<6} {_fmt_ts(u.last_login_at)}")
    return 0


def cmd_rotate_secret(_args) -> int:
    rotate_secret()
    admin_sessions.reload_signer()
    print("Rotated session secret. All existing sessions are now invalid.")
    return 0


def cmd_revoke_sessions(args) -> int:
    user = admin_users.get_by_username(args.username)
    if user is None:
        print(f"ERROR: user not found: {args.username}", file=sys.stderr)
        return 2
    n = admin_sessions.revoke_all_for_user(user.id)
    print(f"Revoked {n} session(s) for {args.username}.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="admin_cli", description="Admin user management.")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("create-user")
    sp.add_argument("username")
    sp.set_defaults(func=cmd_create)

    sp = sub.add_parser("reset-password")
    sp.add_argument("username")
    sp.set_defaults(func=cmd_reset)

    sp = sub.add_parser("lock")
    sp.add_argument("username")
    sp.set_defaults(func=cmd_lock)

    sp = sub.add_parser("unlock")
    sp.add_argument("username")
    sp.set_defaults(func=cmd_unlock)

    sp = sub.add_parser("list-users")
    sp.set_defaults(func=cmd_list)

    sp = sub.add_parser("rotate-secret")
    sp.set_defaults(func=cmd_rotate_secret)

    sp = sub.add_parser("revoke-sessions")
    sp.add_argument("username")
    sp.set_defaults(func=cmd_revoke_sessions)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
