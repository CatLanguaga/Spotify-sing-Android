"""slowapi limiter for /admin/login (per-IP).

Per-username throttling is handled by progressive lockout in users.py
(consecutive-fail counter + locked_until). slowapi here only protects
against IP-level brute force.
"""
from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=[])

LOGIN_PER_IP = "5/15 minutes"
