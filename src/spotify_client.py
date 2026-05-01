"""
Spotify API client for fetching playlist tracks with full metadata
Improved language detection based on artist and all available text
"""
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials


# Known Japanese/Korean labels and keywords
JAPANESE_LABELS = ['sony music japan', 'avex', 'lantis', 'aniplex', 'king records', 'victor', 'pony canyon', 'bushiroad']
KOREAN_LABELS = ['sm entertainment', 'jyp', 'yg entertainment', 'hybe', 'kakao', 'starship']


class SpotifyClient:
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.sp = None
        
    def authenticate(self):
        try:
            auth_manager = SpotifyClientCredentials(
                client_id=self.client_id,
                client_secret=self.client_secret
            )
            self.sp = spotipy.Spotify(auth_manager=auth_manager)
            return True
        except Exception as e:
            print(f"Spotify authentication error: {e}")
            return False
    
    def extract_playlist_id(self, playlist_input):
        if 'spotify.com/playlist/' in playlist_input:
            parts = playlist_input.split('playlist/')
            if len(parts) > 1:
                playlist_id = parts[1].split('?')[0]
                return playlist_id
        return playlist_input
    
    def get_playlist_tracks(self, playlist_id, offset=0, limit=50):
        """Get tracks with full metadata and improved language detection"""
        if not self.sp:
            if not self.authenticate():
                return None
        
        try:
            playlist_id = self.extract_playlist_id(playlist_id)
            
            results = self.sp.playlist_tracks(
                playlist_id,
                offset=offset,
                limit=limit
            )
            
            tracks = []
            for item in results['items']:
                if item['track']:
                    track = item['track']
                    artist = track['artists'][0]['name'] if track['artists'] else 'Unknown'
                    all_artists = ', '.join([a['name'] for a in track['artists']])
                    
                    # Get album info
                    album = track.get('album', {})
                    album_name = album.get('name', 'Unknown Album')
                    
                    # Get album art
                    album_art_url = None
                    if album.get('images'):
                        images = album['images']
                        for img in images:
                            if img.get('width') == 300:
                                album_art_url = img['url']
                                break
                        if not album_art_url:
                            album_art_url = images[0]['url']
                    
                    # Improved language detection
                    # Check: track name, album name, ALL artists
                    language = self._detect_language_smart(
                        track['name'], 
                        album_name, 
                        all_artists
                    )
                    
                    tracks.append({
                        'name': track['name'],
                        'artist': artist,
                        'all_artists': all_artists,
                        'duration_ms': track['duration_ms'],
                        'album': album_name,
                        'album_art_url': album_art_url,
                        'track_number': track.get('track_number', 1),
                        'year': album.get('release_date', '')[:4] if album.get('release_date') else '',
                        'language': language,
                        'spotify_id': track.get('id', '')
                    })
            
            return tracks
            
        except Exception as e:
            print(f"Error fetching playlist tracks: {e}")
            return None
    
    def _detect_language_smart(self, track_name, album_name, artists):
        """
        Smart language detection based on:
        1. Characters in track name, album name, and artist names
        2. Artist names often reveal the language better than track titles
        """
        # Combine all text for analysis
        all_text = f"{track_name} {album_name} {artists}"
        
        # Count characters by script type
        counts = {
            'cjk': 0,        # Chinese/Japanese Kanji
            'hiragana': 0,   # Japanese
            'katakana': 0,   # Japanese
            'hangul': 0,     # Korean
            'cyrillic': 0,   # Russian
            'arabic': 0,     # Arabic
            'latin': 0,      # English/Spanish etc
        }
        
        for char in all_text:
            code = ord(char)
            if 0x4E00 <= code <= 0x9FFF or 0x3400 <= code <= 0x4DBF:
                counts['cjk'] += 1
            elif 0x3040 <= code <= 0x309F:
                counts['hiragana'] += 1
            elif 0x30A0 <= code <= 0x30FF:
                counts['katakana'] += 1
            elif 0xAC00 <= code <= 0xD7AF or 0x1100 <= code <= 0x11FF:
                counts['hangul'] += 1
            elif 0x0400 <= code <= 0x04FF:
                counts['cyrillic'] += 1
            elif 0x0600 <= code <= 0x06FF:
                counts['arabic'] += 1
            elif 0x0041 <= code <= 0x007A or 0x00C0 <= code <= 0x00FF:
                counts['latin'] += 1
        
        # Japanese = hiragana/katakana OR CJK with Japanese context
        japanese_chars = counts['hiragana'] + counts['katakana'] + counts['cjk']
        korean_chars = counts['hangul']
        
        # Priority: Non-Latin scripts first (they're more specific)
        if korean_chars >= 2:
            return 'Korean'
        
        # Check for Japanese (hiragana/katakana are definitive)
        if counts['hiragana'] >= 1 or counts['katakana'] >= 1:
            return 'Japanese/Chinese'  # Match filter option
        
        # CJK without hiragana/katakana could be Chinese or Japanese
        # Check artist name for hints
        if counts['cjk'] >= 2:
            # If artist has Japanese-looking name or common Japanese indicators
            artist_lower = artists.lower()
            if any(jp_indicator in artist_lower for jp_indicator in ['cv.', 'cv:', '(cv', 'feat.', 'starring', 'from']):
                return 'Japanese/Chinese'
            return 'Japanese/Chinese'
        
        if counts['cyrillic'] >= 2:
            return 'Russian'
        
        if counts['arabic'] >= 2:
            return 'Arabic'
        
        # Default to Latin-based
        if counts['latin'] > 0:
            return 'English/Spanish'
        
        return 'Other'
    
    def search_track(self, track_name, artist_name, limit=1):
        """Search for a track on Spotify and return metadata (mainly duration_ms, album art)."""
        if not self.sp:
            if not self.authenticate():
                return None
        try:
            q = f"track:{track_name} artist:{artist_name}"
            results = self.sp.search(q=q, type='track', limit=limit)
            items = results.get('tracks', {}).get('items', [])
            if not items:
                # Fallback: simple query
                results = self.sp.search(q=f"{track_name} {artist_name}", type='track', limit=limit)
                items = results.get('tracks', {}).get('items', [])
            tracks = []
            for track in items:
                album = track.get('album', {})
                album_art_url = None
                if album.get('images'):
                    album_art_url = album['images'][0]['url']
                all_artists = ', '.join([a['name'] for a in track['artists']])
                tracks.append({
                    'name': track['name'],
                    'artist': track['artists'][0]['name'] if track['artists'] else artist_name,
                    'all_artists': all_artists,
                    'duration_ms': track['duration_ms'],
                    'album': album.get('name', ''),
                    'album_art_url': album_art_url,
                    'track_number': track.get('track_number', 1),
                    'year': album.get('release_date', '')[:4] if album.get('release_date') else '',
                })
            return tracks
        except Exception as e:
            print(f"Spotify search error: {e}")
            return None

    def get_playlist_info(self, playlist_id):
        if not self.sp:
            if not self.authenticate():
                return None
        
        try:
            playlist_id = self.extract_playlist_id(playlist_id)
            playlist = self.sp.playlist(playlist_id, fields='name,tracks.total')
            
            return {
                'name': playlist['name'],
                'total_tracks': playlist['tracks']['total']
            }
        except Exception as e:
            print(f"Error fetching playlist info: {e}")
            return None
