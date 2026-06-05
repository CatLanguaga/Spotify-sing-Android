"""
Configuration manager for storing and loading API credentials and settings
"""
import logging
import os
import json
from pathlib import Path

MAX_TRACKS_PER_REQUEST = int(os.environ.get('MAX_TRACKS_PER_REQUEST', '50'))
MAX_CONCURRENT_DOWNLOADS_DEFAULT = int(os.environ.get('SPOTIFY_MAX_CONCURRENT_DOWNLOADS', '3'))

_log = logging.getLogger(__name__)

# Optional at-rest encryption for sensitive fields (currently: spotify_client_secret).
# Lives in gui/backend/admin/crypto.py — a soft import keeps src/config.py usable
# from the legacy CLI even if the admin package isn't installed.
try:
    from gui.backend.admin.crypto import (
        encrypt as _crypto_encrypt,
        is_encrypted as _crypto_is_encrypted,
        try_decrypt as _crypto_try_decrypt,
    )
    _CRYPTO_AVAILABLE = True
except Exception:  # pragma: no cover
    _CRYPTO_AVAILABLE = False

    def _crypto_encrypt(s):  # type: ignore[no-redef]
        return s

    def _crypto_is_encrypted(s):  # type: ignore[no-redef]
        return False

    def _crypto_try_decrypt(s):  # type: ignore[no-redef]
        return s


def _encrypt_secret(value):
    """Encrypt a secret value if crypto is wired and value isn't already a ciphertext."""
    if not value or not _CRYPTO_AVAILABLE:
        return value
    if _crypto_is_encrypted(value):
        return value
    try:
        return _crypto_encrypt(value)
    except Exception as e:
        _log.warning("Failed to encrypt secret, storing plaintext: %s", e)
        return value


def _decrypt_secret(value):
    """Decrypt a secret value if it's an at-rest ciphertext, else return as-is."""
    if not value or not _CRYPTO_AVAILABLE:
        return value
    try:
        return _crypto_try_decrypt(value)
    except Exception as e:
        _log.error("Failed to decrypt secret (wrong key or tampered): %s", e)
        return None


class ConfigManager:
    def __init__(self):
        # Priority for the config file path:
        #   1. SPOTIFY_CONFIG_FILE env (explicit absolute path)
        #   2. SPOTIFY_CONFIG_DIR env  (file = <dir>/config.json)
        #   3. ANDROID_STORAGE env     (legacy mobile)
        #   4. ~/.spotifytoyoutube      (legacy dev)
        #
        # Docker/Coolify deployments set SPOTIFY_CONFIG_DIR=/app/data so the file
        # lives in the persistent volume and credentials survive redeploys.
        env_file = os.environ.get('SPOTIFY_CONFIG_FILE')
        env_dir = os.environ.get('SPOTIFY_CONFIG_DIR')
        if env_file:
            self.config_file = Path(env_file)
            self.config_dir = self.config_file.parent
        elif env_dir:
            self.config_dir = Path(env_dir)
            self.config_file = self.config_dir / 'config.json'
        elif 'ANDROID_STORAGE' in os.environ:
            self.config_dir = Path(os.environ['ANDROID_STORAGE']) / 'spotifytoyoutube'
            self.config_file = self.config_dir / 'config.json'
        else:
            self.config_dir = Path.home() / '.spotifytoyoutube'
            self.config_file = self.config_dir / 'config.json'

        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.default_download_folder = str(Path.home() / 'Music' / 'SpotifyYT')
        
    def save_config(self, spotify_client_id, spotify_client_secret, download_folder=None,
                    playlist_id=None, default_fmt=None, default_quality=None,
                    default_range_from=None, default_range_to=None,
                    manual_review_enabled=None, max_concurrent_downloads=None):
        """Save API credentials and settings - YouTube API no longer needed"""
        existing = self.load_config() or {}

        config = {
            'spotify_client_id': spotify_client_id,
            'spotify_client_secret': _encrypt_secret(spotify_client_secret),
            'download_folder': download_folder or existing.get('download_folder', self.default_download_folder),
            'playlist_id': playlist_id if playlist_id is not None else existing.get('playlist_id', ''),
            'default_fmt': default_fmt if default_fmt is not None else existing.get('default_fmt', 'mp3'),
            'default_quality': default_quality if default_quality is not None else existing.get('default_quality', 320),
            'default_range_from': default_range_from if default_range_from is not None else existing.get('default_range_from', 1),
            'default_range_to': default_range_to if default_range_to is not None else existing.get('default_range_to', None),
            'manual_review_enabled': manual_review_enabled if manual_review_enabled is not None else existing.get('manual_review_enabled', False),
            'max_concurrent_downloads': max(1, min(5, int(
                max_concurrent_downloads if max_concurrent_downloads is not None
                else existing.get('max_concurrent_downloads', MAX_CONCURRENT_DOWNLOADS_DEFAULT)
            ))),
        }

        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
    
    def migrate_at_rest_encryption(self):
        """Re-encrypt the on-disk spotify_client_secret if it's still plaintext.

        Idempotent: skipped when crypto isn't available or the secret is already
        encrypted (v1: prefix). Returns True when a migration was performed.
        """
        if not _CRYPTO_AVAILABLE or not self.config_file.exists():
            return False
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                raw = json.load(f) or {}
        except Exception:
            return False
        secret = raw.get('spotify_client_secret')
        if not secret or _crypto_is_encrypted(secret):
            return False
        try:
            raw['spotify_client_secret'] = _crypto_encrypt(secret)
        except Exception as e:
            _log.warning("At-rest migration failed: %s", e)
            return False
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(raw, f, indent=2)
        _log.info("Migrated spotify_client_secret to at-rest encryption.")
        return True

    def save_download_folder(self, folder_path):
        """Save only the download folder setting"""
        config = self.load_config() or {}
        config['download_folder'] = folder_path
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
    
    def get_download_folder(self):
        """Get the download folder path"""
        config = self.load_config()
        if config and config.get('download_folder'):
            return config['download_folder']
        return self.default_download_folder
    
    def load_config(self):
        """Load config, with environment variables taking priority over the file.

        Deploy (single-tenant) sets SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET and
        optionally DOWNLOAD_DIR; these override anything stored in config.json so the
        container has no writable-config dependency. For local dev (no env vars) the
        on-disk config.json is used as before.
        Returns a dict, or None when neither source provides credentials.
        """
        file_config = {}
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    file_config = json.load(f) or {}
            except Exception:
                file_config = {}

        # Decrypt at-rest secret if it's a versioned ciphertext.
        stored_secret = file_config.get('spotify_client_secret')
        if stored_secret:
            file_config['spotify_client_secret'] = _decrypt_secret(stored_secret)

        env_id = os.environ.get('SPOTIFY_CLIENT_ID')
        env_secret = os.environ.get('SPOTIFY_CLIENT_SECRET')
        env_download = os.environ.get('DOWNLOAD_DIR')
        env_concurrency = os.environ.get('SPOTIFY_MAX_CONCURRENT_DOWNLOADS')

        if env_id:
            file_config['spotify_client_id'] = env_id
        if env_secret:
            file_config['spotify_client_secret'] = env_secret
        if env_download:
            file_config['download_folder'] = env_download
        if env_concurrency and 'max_concurrent_downloads' not in file_config:
            try:
                file_config['max_concurrent_downloads'] = max(1, min(5, int(env_concurrency)))
            except ValueError:
                pass

        return file_config or None

    def has_config(self):
        """Check if config exists with Spotify credentials"""
        config = self.load_config()
        if not config:
            return False

        # Only Spotify credentials are required now
        return all([
            config.get('spotify_client_id'),
            config.get('spotify_client_secret')
        ])
