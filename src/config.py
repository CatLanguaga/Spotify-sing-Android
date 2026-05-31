"""
Configuration manager for storing and loading API credentials and settings
"""
import os
import json
from pathlib import Path

MAX_TRACKS_PER_REQUEST = int(os.environ.get('MAX_TRACKS_PER_REQUEST', '50'))


class ConfigManager:
    def __init__(self):
        if hasattr(os, 'environ') and 'ANDROID_STORAGE' in os.environ:
            self.config_dir = Path(os.environ['ANDROID_STORAGE']) / 'spotifytoyoutube'
        else:
            self.config_dir = Path.home() / '.spotifytoyoutube'
        
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / 'config.json'
        self.default_download_folder = str(Path.home() / 'Music' / 'SpotifyYT')
        
    def save_config(self, spotify_client_id, spotify_client_secret, download_folder=None,
                    playlist_id=None, default_fmt=None, default_quality=None,
                    default_range_from=None, default_range_to=None,
                    manual_review_enabled=None):
        """Save API credentials and settings - YouTube API no longer needed"""
        existing = self.load_config() or {}

        config = {
            'spotify_client_id': spotify_client_id,
            'spotify_client_secret': spotify_client_secret,
            'download_folder': download_folder or existing.get('download_folder', self.default_download_folder),
            'playlist_id': playlist_id if playlist_id is not None else existing.get('playlist_id', ''),
            'default_fmt': default_fmt if default_fmt is not None else existing.get('default_fmt', 'mp3'),
            'default_quality': default_quality if default_quality is not None else existing.get('default_quality', 320),
            'default_range_from': default_range_from if default_range_from is not None else existing.get('default_range_from', 1),
            'default_range_to': default_range_to if default_range_to is not None else existing.get('default_range_to', None),
            'manual_review_enabled': manual_review_enabled if manual_review_enabled is not None else existing.get('manual_review_enabled', False),
        }

        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
    
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
        """Load config from file"""
        if not self.config_file.exists():
            return None
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None
    
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
