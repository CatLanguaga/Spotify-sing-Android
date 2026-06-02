"""
Spotify API client for fetching playlist tracks with full metadata
Improved language detection based on artist and all available text
"""
import re
import unicodedata

import spotipy
import requests
from spotipy.oauth2 import SpotifyClientCredentials

try:
    from langdetect import detect_langs, DetectorFactory
    from langdetect.lang_detect_exception import LangDetectException
    # langdetect is non-deterministic by default; seed for stable results.
    DetectorFactory.seed = 0
    _LANGDETECT_OK = True
except Exception:  # pragma: no cover - optional dependency
    _LANGDETECT_OK = False
    LangDetectException = Exception


# Known Japanese/Korean labels and keywords
JAPANESE_LABELS = ['sony music japan', 'avex', 'lantis', 'aniplex', 'king records', 'victor', 'pony canyon', 'bushiroad']
KOREAN_LABELS = ['sm entertainment', 'jyp', 'yg entertainment', 'hybe', 'kakao', 'starship']

# langdetect ISO codes → display names used by the UI / filters.
_LANG_CODE_TO_NAME = {
    'es': 'Spanish', 'en': 'English', 'pt': 'Portuguese',
    'it': 'Italian', 'fr': 'French',
}
# Min confidence to trust langdetect's top guess for short metadata strings.
_LANGDETECT_MIN_CONF = 0.85
_STOPWORD_MIN_SCORE = 2

GENRE_LANGUAGE_HINTS = {
    'Spanish': {
        'bachata', 'cumbia', 'corridos', 'dominican', 'latin hip hop',
        'latin pop', 'latin rock', 'latino', 'mexican', 'musica mexicana',
        'puerto rican', 'reggaeton', 'regional mexican', 'salsa',
        'spanish pop', 'trap latino', 'urbano latino',
    },
    'Portuguese': {
        'bossa nova', 'brasil', 'brazil', 'brazilian', 'forro',
        'funk carioca', 'mpb', 'pagode', 'sertanejo',
    },
    'Italian': {'italian'},
    'French': {'french', 'francais', 'francophone'},
    'Korean': {'k-pop', 'korean'},
    'Japanese/Chinese': {
        'anime', 'j-pop', 'j-rock', 'japanese', 'otacore', 'vocaloid',
    },
}

# Expanded stopword sets for the fallback heuristic (scoring, not first-match).
STOPWORDS = {
    'English': {
        'a', 'all', 'am', 'and', 'another', 'are', 'be', 'been', 'blue',
        'baby', 'birthday', 'bones', 'boy', 'bridges', 'burning', 'cheap',
        'day', 'dear', 'deeds', 'did', 'didnt', 'dirty', 'diver', 'do',
        'does', 'done', 'dont', 'dragons', 'dust', 'fire', 'for', 'gangstas', 'get', 'girl',
        'god', 'gotta', 'have', 'heaven', 'hell', 'holy', 'i', 'in', 'is',
        'idle', 'imagine', 'it', 'its', 'kindness', 'life', 'little', 'love', 'lucille',
        'lucky', 'man', 'me', 'mirror', 'my', 'of', 'on', 'one', 'our',
        'paradise', 'piano', 'skeletons', 'sky', 'someday', 'start', 'teen',
        'tenacious', 'tenderness', 'the', 'to', 'train', 'tribute', 'try', 'up', 'us',
        'wake', 'want', 'was', 'we', 'were', 'whats', 'with', 'without',
        'woman', 'world', 'you', 'your',
    },
    'Spanish': {
        'amor', 'baila', 'bailando', 'beso', 'cancion', 'corazon', 'contigo',
        'de', 'del', 'el', 'ella', 'eres', 'esta', 'la', 'las', 'lo', 'los',
        'mi', 'noche', 'para', 'por', 'que', 'sin', 'te', 'tu', 'una', 'uno',
        'vida', 'yo', 'con', 'mas', 'muy', 'nada', 'todo', 'soy', 'estoy',
        'ahi', 'alma', 'amiga', 'amigo', 'aqui', 'ayer', 'bachata',
        'bailar', 'bebe', 'bien', 'calle', 'cielo', 'como', 'cuando',
        'dame', 'diablo', 'dime', 'dios', 'donde', 'duro', 'feliz',
        'gasolina', 'hasta', 'hombre', 'hoy', 'llora', 'llorar', 'llorando',
        'loca', 'loco', 'mal', 'manana', 'me', 'mis', 'mujer', 'nunca',
        'perreo', 'quiero', 'quieres', 'quiere', 'rumba', 'se', 'si',
        'su', 'sus', 'triste', 'tus', 'agua', 'al', 'carnaval', 'chino',
        'amigos', 'arbol', 'decir', 'dia', 'entrevista', 'infinito',
        'ininteligible', 'inmortal', 'luna', 'ni', 'nos', 'podiamos', 'quien',
        'realidad', 'revoloteando', 'roja', 'ser', 'siquiera', 'soledad',
        'suaves', 'susurros', 'veremos', 'volverte',
        'viejos', 'viaje',
    },
    'Portuguese': {
        'voce', 'nao', 'sim', 'coracao', 'saudade', 'amor', 'mais', 'muito',
        'com', 'sem', 'para', 'por', 'que', 'uma', 'um', 'meu', 'minha',
        'noite', 'vida', 'tudo', 'nada', 'ela', 'ele', 'eu', 'nos', 'da', 'do',
        'amigos', 'milhao',
    },
    'Italian': {
        'amore', 'cuore', 'notte', 'vita', 'sono', 'che', 'non', 'con', 'per',
        'una', 'uno', 'mio', 'mia', 'tu', 'io', 'noi', 'sempre', 'piu', 'cosa',
        'della', 'questo', 'tutto', 'niente',
    },
    'French': {
        'amour', 'coeur', 'nuit', 'vie', 'je', 'tu', 'nous', 'vous', 'avec',
        'sans', 'pour', 'que', 'une', 'un', 'mon', 'ma', 'toujours', 'rien',
        'tout', 'cest', 'pas', 'les', 'des', 'du', 'le', 'tous', 'garcons',
        'filles',
    },
}
# Back-compat alias (older code referenced SPANISH_HINTS directly).
SPANISH_HINTS = STOPWORDS['Spanish']


def _strip_accents(text):
    return ''.join(
        char for char in unicodedata.normalize('NFKD', text)
        if not unicodedata.combining(char)
    )


def _tokenize(text):
    return set(re.findall(r"[a-z0-9]+", _strip_accents(text.lower().replace("'", ""))))


class SpotifyClient:
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.sp = None
        
    def authenticate(self):
        try:
            session = requests.Session()
            session.trust_env = False
            auth_manager = SpotifyClientCredentials(
                client_id=self.client_id,
                client_secret=self.client_secret,
                requests_session=session,
            )
            self.sp = spotipy.Spotify(auth_manager=auth_manager, requests_session=session)
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

            artist_ids = []
            for item in results['items']:
                track = item.get('track')
                if not track:
                    continue
                artist_ids.extend(
                    artist.get('id') for artist in track.get('artists', [])
                    if artist.get('id')
                )
            genres_by_artist = self._get_artist_genres(artist_ids)
            
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
                    artist_genres = sorted({
                        genre
                        for a in track.get('artists', [])
                        for genre in genres_by_artist.get(a.get('id'), [])
                    })

                    # Improved language detection
                    # Check: track name, album name, ALL artists, and artist genres.
                    language = self._detect_language_smart(
                        track['name'], 
                        album_name, 
                        all_artists,
                        artist_genres,
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
                        'lyrics': track.get('lyrics') or track.get('lyrics_text') or '',
                        'language': language,
                        'spotify_id': track.get('id', '')
                    })
            
            return tracks
            
        except Exception as e:
            print(f"Error fetching playlist tracks: {e}")
            return None

    def _get_artist_genres(self, artist_ids):
        """Fetch Spotify artist genres in batches. Missing genres are harmless."""
        if not self.sp:
            return {}

        unique_ids = []
        seen = set()
        for artist_id in artist_ids:
            if artist_id and artist_id not in seen:
                seen.add(artist_id)
                unique_ids.append(artist_id)

        genres_by_artist = {}
        try:
            for start in range(0, len(unique_ids), 50):
                batch = unique_ids[start:start + 50]
                if not batch:
                    continue
                artists = self.sp.artists(batch).get('artists', [])
                for artist in artists:
                    if artist and artist.get('id'):
                        genres_by_artist[artist['id']] = artist.get('genres') or []
        except Exception as e:
            print(f"Spotify artist genre lookup warning: {e}")

        return genres_by_artist
    
    def _detect_language_smart(self, track_name, album_name, artists, genres=None):
        """
        Smart language detection based on:
        1. Characters in track name, album name, and artist names
        2. Artist names and genres often reveal the language better than titles
        """
        # Combine all text for analysis
        all_text = f"{track_name} {album_name} {artists}"
        genres = genres or []
        
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

        genre_lang = self._detect_language_from_genres(genres)
        if genre_lang:
            return genre_lang
        
        # Latin script: try langdetect first, fall back to stopword scoring.
        if counts['latin'] > 0:
            return self._detect_latin_language(track_name, album_name, artists)

        return 'Other'

    def _detect_language_from_genres(self, genres):
        genre_text = ' | '.join(genres).lower()
        if not genre_text:
            return None

        for language, hints in GENRE_LANGUAGE_HINTS.items():
            if language in {'French', 'Italian'}:
                continue
            if any(hint in genre_text for hint in hints):
                return language
        return None

    def _detect_latin_language(self, track_name, album_name='', artists=''):
        """Classify Latin-script text (es/en/pt/it/fr) — no blind English default.

        Order matters. On short song metadata `langdetect` is wildly
        overconfident (it tags "La Vie En Rose" as English 0.9999 and "XO" as
        Somali), so trusting it first reintroduces the very misclassification
        we're fixing. Instead:

        1. High-precision stopword scoring across {en, es, pt, it, fr}. A
           unique winner wins only after a minimum score.
        2. `langdetect` only as a fallback/tiebreaker, and only when it picks a
           language we map (so garbage like Somali → 'Other', not English).
           langdetect is trusted only with high confidence.
        3. Anything ambiguous → 'Other'. Never a blind English default.
        """
        all_text = f"{track_name} {album_name} {artists}"
        text_lower = all_text.lower()

        # 1. Stopword scoring (high precision for the target languages).
        words = _tokenize(all_text)

        scores = {lang: len(words & stops) for lang, stops in STOPWORDS.items()}
        if 'ñ' in text_lower:  # strong Spanish signal
            scores['Spanish'] += 2

        best_score = max(scores.values())
        winners = [lang for lang, s in scores.items() if s == best_score]

        # 2. Top mapped langdetect candidate (used only as fallback/tiebreak).
        ld_lang = None
        ld_prob = 0.0
        if _LANGDETECT_OK and len(text_lower.replace(' ', '')) >= 8:
            try:
                for cand in detect_langs(all_text):
                    if cand.lang in _LANG_CODE_TO_NAME:
                        ld_lang = _LANG_CODE_TO_NAME[cand.lang]
                        ld_prob = cand.prob
                        break
            except LangDetectException:
                pass

        if best_score >= _STOPWORD_MIN_SCORE:
            if len(winners) == 1:
                return winners[0]
            # Tie between languages → let langdetect break it if it agrees.
            return ld_lang if ld_lang in winners else 'Other'

        # 3. Low/no stopword signal: rely on langdetect only where it is less
        # likely to confuse Spanish song metadata with nearby Romance languages.
        if ld_lang and ld_prob >= _LANGDETECT_MIN_CONF:
            if ld_lang in {'English', 'Spanish'}:
                return ld_lang
            if scores.get(ld_lang, 0) >= _STOPWORD_MIN_SCORE:
                return ld_lang
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
