#!/usr/bin/env python3
"""Verify admin hardening posture.

Checks env vars, file perms on data/.session_secret + data/.data_key, and
whether the DB has at least one admin user. Reports per-check status:

    [OK]    everything correct
    [WARN]  works, but production should tighten
    [FAIL]  broken / dangerous default

Exit code: 0 if no FAIL, 1 otherwise. Safe to run in CI / healthcheck cron.

Usage:
    python tools/check-admin-hardening.py
    python tools/check-admin-hardening.py --prod    # treat WARN as FAIL
"""
from __future__ import annotations

import argparse
import os
import stat
import sys
from pathlib import Path

# Make repo root importable when run as a script.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

OK = "[OK]   "
WARN = "[WARN] "
FAIL = "[FAIL] "


class Report:
    def __init__(self) -> None:
        self.fails = 0
        self.warns = 0

    def ok(self, msg: str) -> None:
        print(OK + msg)

    def warn(self, msg: str) -> None:
        self.warns += 1
        print(WARN + msg)

    def fail(self, msg: str) -> None:
        self.fails += 1
        print(FAIL + msg)


def _env(name: str) -> str:
    return os.environ.get(name, "").strip()


def _envset(name: str) -> bool:
    return bool(_env(name))


def _flag(name: str) -> bool:
    return _env(name).lower() in {"1", "true", "yes"}


def check_envs(r: Report) -> None:
    print("\n== Env vars ==")

    # Required-ish in production
    if _envset("ADMIN_SESSION_SECRET"):
        if len(_env("ADMIN_SESSION_SECRET")) < 32:
            r.fail("ADMIN_SESSION_SECRET set but < 32 chars.")
        else:
            r.ok("ADMIN_SESSION_SECRET set (>= 32 chars).")
    else:
        r.warn("ADMIN_SESSION_SECRET unset — auto-generated key on disk. "
               "Set explicitly in prod so a leaked container image doesn't expose the file.")

    if _envset("ADMIN_DATA_KEY"):
        r.ok("ADMIN_DATA_KEY set (used for at-rest encryption).")
    else:
        r.warn("ADMIN_DATA_KEY unset — auto-generated key on disk. "
               "Set explicitly in prod and store off-box (otherwise a single backup leaks both data + key).")

    if _envset("ADMIN_META_PEPPER"):
        r.ok("ADMIN_META_PEPPER set (audit log uses non-default pepper).")
    else:
        r.warn("ADMIN_META_PEPPER unset — audit hashes use a known default pepper.")

    if _flag("ADMIN_COOKIE_SECURE"):
        r.ok("ADMIN_COOKIE_SECURE=1 (cookies issued with Secure + __Host- prefix).")
    else:
        r.fail("ADMIN_COOKIE_SECURE not enabled — cookies will be sent over plain HTTP.")

    if _flag("SECURITY_HEADERS_STRICT"):
        r.ok("SECURITY_HEADERS_STRICT=1 (HSTS + CSP enabled).")
    else:
        r.warn("SECURITY_HEADERS_STRICT off — HSTS/CSP not emitted.")

    if _flag("FORCE_HTTPS"):
        r.ok("FORCE_HTTPS=1.")
    else:
        r.warn("FORCE_HTTPS off — plain-HTTP requests aren't redirected.")

    # ADMIN_PASSWORD usage
    if _envset("ADMIN_PASSWORD"):
        r.warn("ADMIN_PASSWORD still set — used as one-shot seed on a fresh DB. "
               "Remove it after first boot once the DB has the admin user.")
    else:
        r.ok("ADMIN_PASSWORD not set in current process env (good after bootstrap).")

    # Stealth / footer (informational, off by default in dev)
    if _flag("ADMIN_STEALTH"):
        r.ok("ADMIN_STEALTH=1 (admin surface returns 404 when unauth).")
    else:
        r.warn("ADMIN_STEALTH off — /api/admin/* leak existence via 401/403.")

    if _env("ADMIN_FOOTER_LINK").lower() == "false":
        r.ok("ADMIN_FOOTER_LINK=false (Admin link hidden in footer).")
    else:
        r.warn("ADMIN_FOOTER_LINK enabled (visible to all visitors).")


def check_file(r: Report, path: Path, label: str, required: bool = False) -> None:
    if not path.exists():
        if required:
            r.fail(f"{label} missing: {path}")
        else:
            r.ok(f"{label} not on disk (overridden by env or not yet generated): {path}")
        return
    st = path.stat()
    size = st.st_size
    if size < 16:
        r.fail(f"{label} suspiciously small ({size} bytes): {path}")
        return
    mode = stat.S_IMODE(st.st_mode)
    # On POSIX we want 0600. On Windows perms are mostly meaningless.
    if os.name == "posix":
        if mode & 0o077:
            r.fail(f"{label} world/group-readable (mode {oct(mode)}): {path}")
        else:
            r.ok(f"{label} present, mode {oct(mode)}: {path}")
    else:
        r.warn(f"{label} present on Windows host — POSIX perms not enforceable: {path}")


def check_files(r: Report) -> None:
    print("\n== Key files ==")
    data_dir = Path(os.environ.get("SPOTIFY_CONFIG_DIR",
                    Path(os.environ.get("ADMIN_DB_PATH", "data/admin.sqlite3")).parent))
    check_file(r, data_dir / ".session_secret", "session secret")
    check_file(r, data_dir / ".data_key", "at-rest data key")


def check_db(r: Report) -> None:
    print("\n== DB ==")
    try:
        from gui.backend.admin import users
        n = users.count_users()
    except Exception as e:
        r.fail(f"DB unreachable: {e}")
        return
    if n == 0:
        r.fail("No admin users in DB. Set ADMIN_PASSWORD (seed) or run admin_cli create-user.")
    elif n == 1:
        r.ok("Exactly 1 admin user provisioned.")
    else:
        r.ok(f"{n} admin users provisioned.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prod", action="store_true",
                        help="Treat WARN as FAIL (stricter exit code).")
    args = parser.parse_args()

    r = Report()
    check_envs(r)
    check_files(r)
    check_db(r)

    print()
    print(f"Summary: {r.fails} fail(s), {r.warns} warn(s).")
    if r.fails or (args.prod and r.warns):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
