"""Symmetric encryption for at-rest sensitive values.

Wraps `cryptography.fernet.Fernet` (AES-128-CBC + HMAC-SHA256 + signed
timestamp). All ciphertexts carry a `v1:` prefix so we can rotate algorithms
in the future without breaking old blobs.

Key loading priority:
    1. ADMIN_DATA_KEY env (Fernet key — 32 url-safe bytes, base64)
    2. data/.data_key file (auto-generated, perms 0600)

Deliberately separate from the session-signing secret (`.session_secret`)
so a leak of one does not cascade. Backups that include `data/` but exclude
`.data_key` (or `ADMIN_DATA_KEY` env) are useless — desired property.

Public surface:
    encrypt(plaintext) -> "v1:..." string  (safe to store in JSON/SQL)
    decrypt(blob)      -> plaintext (raises CryptoError on tamper/wrong key)
    is_encrypted(blob) -> bool             (cheap prefix check)
    reload_key()                           (call after rotation)
"""
from __future__ import annotations

import logging
import os
import stat
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from .db import DB_PATH

log = logging.getLogger(__name__)

_KEY_FILE = DB_PATH.parent / ".data_key"
_VERSION_PREFIX = "v1:"

_cipher: Optional[Fernet] = None


class CryptoError(Exception):
    pass


def _load_or_create_key() -> bytes:
    env_val = os.environ.get("ADMIN_DATA_KEY")
    if env_val:
        raw = env_val.strip().encode("ascii")
        # Validate format by attempting to instantiate Fernet
        try:
            Fernet(raw)
            return raw
        except Exception as e:
            raise CryptoError(
                "ADMIN_DATA_KEY env is not a valid Fernet key (must be "
                "url-safe base64 of 32 bytes). Generate with "
                "`python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"`."
            ) from e

    if _KEY_FILE.exists():
        data = _KEY_FILE.read_bytes().strip()
        try:
            Fernet(data)
            return data
        except Exception:
            log.warning("data key file corrupt, regenerating: %s", _KEY_FILE)

    _KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    new_key = Fernet.generate_key()
    _KEY_FILE.write_bytes(new_key)
    try:
        os.chmod(_KEY_FILE, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass
    log.info("Generated new at-rest data key at %s", _KEY_FILE)
    return new_key


def _get_cipher() -> Fernet:
    global _cipher
    if _cipher is None:
        _cipher = Fernet(_load_or_create_key())
    return _cipher


def reload_key() -> None:
    """Force re-read after rotation. Existing ciphertexts will fail to decrypt
    unless the new key matches — caller is responsible for re-encrypting."""
    global _cipher
    _cipher = None


def encrypt(plaintext: str) -> str:
    if plaintext is None:
        raise CryptoError("Cannot encrypt None.")
    token = _get_cipher().encrypt(plaintext.encode("utf-8"))
    return _VERSION_PREFIX + token.decode("ascii")


def decrypt(blob: str) -> str:
    if not isinstance(blob, str) or not blob.startswith(_VERSION_PREFIX):
        raise CryptoError("Not a versioned ciphertext.")
    try:
        plain = _get_cipher().decrypt(blob[len(_VERSION_PREFIX):].encode("ascii"))
    except InvalidToken as e:
        raise CryptoError("Decryption failed: wrong key or tampered ciphertext.") from e
    return plain.decode("utf-8")


def is_encrypted(blob: object) -> bool:
    return isinstance(blob, str) and blob.startswith(_VERSION_PREFIX)


def try_decrypt(blob: object) -> Optional[str]:
    """Decrypt if it's a ciphertext, else return the value unchanged (str) or None."""
    if blob is None:
        return None
    if not isinstance(blob, str):
        return None
    if is_encrypted(blob):
        return decrypt(blob)
    return blob
