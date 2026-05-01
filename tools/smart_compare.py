import os
import sys
import json
import subprocess
import re
from pathlib import Path
from thefuzz import fuzz
from unidecode import unidecode

# tools/ está un nivel abajo de la raíz del proyecto donde vive src/
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.spotify_client import SpotifyClient

CONFIG_PATH = Path.home() / '.spotifytoyoutube' / 'config.json'
PHONE_MUSIC_DIR = "/storage/emulated/0/snaptube/download/Snaptube Audio"
BLACKLIST_PATH = Path(__file__).parent.parent / 'data' / 'blacklist.json'
COMPARE_LOG_PATH = Path(__file__).parent.parent / 'reports' / 'compare_log.txt'

# ─── LIVE LOG ──────────────────────────────────────────────────────────────────

class TeeLogger:
    def __init__(self, log_path):
        self.log = open(log_path, 'w', encoding='utf-8', buffering=1)
        self._stdout = sys.stdout
    def write(self, msg):
        self._stdout.write(msg); self._stdout.flush()
        self.log.write(msg); self.log.flush()
    def flush(self):
        self._stdout.flush()
        if not self.log.closed:
            self.log.flush()
    def close(self):
        if not self.log.closed:
            self.log.close()

def open_live_log_window(log_path):
    Path(log_path).touch()
    subprocess.Popen(
        f'start "Log en vivo - Comparacion" cmd /k powershell -NoExit -Command "Get-Content -Path \'{log_path}\' -Wait"',
        shell=True
    )
    import time; time.sleep(0.5)

# Palabras a ignorar en la comparación para reducir ruido
IGNORE_TERMS = [
    "official video", "official audio", "official music video", "video oficial",
    "lyric video", "lyrics", "letra", "audio", "hd", "hq", "4k", "remaster", 
    "remastered", "live", "en vivo", "feat", "ft.", "full version", 
    "ost", "original soundtrack", "op", "ed", "opening", "ending",
    "sub español", "subtitulado", "cover", "full"
]

def load_config():
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

def load_blacklist():
    """Carga la lista negra de canciones ya descargadas/presentes que el fuzzy no detecta."""
    if not BLACKLIST_PATH.exists():
        return set()
    entries = json.loads(BLACKLIST_PATH.read_text(encoding='utf-8'))
    # Normalizar a (name_lower, artist_lower) para comparación case-insensitive
    return {(e['name'].lower(), e['artist'].lower()) for e in entries}

def is_blacklisted(track, blacklist):
    key = (track['name'].lower(), track['artist'].lower())
    return key in blacklist

def get_phone_files():
    """List files in the phone music directory"""
    try:
        # Quote path for ADB shell to handle spaces
        # Pasar como string único a adb shell para que maneje el espacio en el path
        cmd = ['adb', 'shell', f'ls -1 "{PHONE_MUSIC_DIR}"']
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
        
        if result.returncode != 0:
            print("Error listing phone files")
            return []
            
        files = result.stdout.strip().split('\n')
        # Filtrar solo audio y limpiar espacios
        return [f.strip() for f in files if f.strip().lower().endswith(('.mp3', '.m4a', '.flac', '.wav'))]
    except Exception as e:
        print(f"Error accessing phone: {e}")
        return []

def clean_string(s):
    """Normaliza un string para comparación difusa."""
    if not s: return ""
    # Decodificar caracteres unicode a ASCII (quita tildes, ñ -> n, etc)
    s = unidecode(s)
    s = s.lower()
    # Quitar extensiones
    s = re.sub(r'\.(mp3|m4a|flac|wav)$', '', s)
    # Quitar términos basura
    for term in IGNORE_TERMS:
        s = s.replace(term, "")
    # Quitar caracteres especiales pero dejar espacios
    s = re.sub(r'[^\w\s]', ' ', s)
    # Colapsar espacios múltiples
    return " ".join(s.split())

def clean_string_raw(s):
    """Limpieza básica SIN quitar caracteres unicode (para comparar japonés/kanjis)."""
    if not s: return ""
    s = s.lower()
    s = re.sub(r'\.(mp3|m4a|flac|wav)$', '', s)
    for term in IGNORE_TERMS:
        s = s.replace(term, "")
    # Mantener caracteres CJK pero quitar símbolos raros si se quiere, 
    # pero mejor dejar pasar la mayoría.
    s = re.sub(r'[^\w\s\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff]', ' ', s) 
    return " ".join(s.split())

def _strip_quality(s):
    """Quita ruido de calidad: mp3, 320k, números sueltos."""
    s = s.replace('_', ' ')  # mp3_320k -> mp3 320k (underscore es \w, no se separa solo)
    s = re.sub(r'\b(mp3|m4a|flac|wav|320k?|128k?|192k?|256k?)\b', '', s)
    s = re.sub(r'\b\d+\b', '', s)
    return ' '.join(s.split())

def is_fuzzy_match(spotify_track, filename):
    artist = spotify_track['artist']
    title  = spotify_track['name']

    clean_art   = clean_string(artist)
    clean_tit   = clean_string(title)
    raw_art     = clean_string_raw(artist)
    raw_tit     = clean_string_raw(title)
    title_words = len(clean_tit.split())

    # ── RAMA A: Filename CON " - " o " _ " → comparación estructurada + artista ──
    # " _ " es separador alternativo usado por algunos videos (ej: "Mar1k0n _ Piter-G")
    has_separator = ' - ' in filename or ' _ ' in filename
    if has_separator:
        fn_s = re.sub(r'\([^)]*\)', '', filename)
        fn_s = re.sub(r'\.(mp3|m4a|flac|wav)$', '', fn_s, flags=re.IGNORECASE).strip()
        # Normalizar separador " _ " a " - " para unificar el split
        fn_s = fn_s.replace(' _ ', ' - ')
        raw_parts = [p.strip() for p in fn_s.split(' - ') if p.strip()]
        c_parts   = [clean_string(p)     for p in raw_parts]
        r_parts   = [clean_string_raw(p) for p in raw_parts]

        # partial_ratio captura "Payphone" dentro de "Payphone ft. Wiz Khalifa"
        for i in range(len(c_parts)):
            for j in range(len(c_parts)):
                if i == j: continue
                t_c = max(fuzz.token_sort_ratio(clean_tit, c_parts[i]),
                          fuzz.partial_ratio(clean_tit,    c_parts[i]))
                a_c = max(fuzz.token_sort_ratio(clean_art, c_parts[j]),
                          fuzz.partial_ratio(clean_art,    c_parts[j]))
                t_r = max(fuzz.token_sort_ratio(raw_tit,   r_parts[i]),
                          fuzz.partial_ratio(raw_tit,      r_parts[i]))
                a_r = max(fuzz.token_sort_ratio(raw_art,   r_parts[j]),
                          fuzz.partial_ratio(raw_art,      r_parts[j]))
                if max(t_c, t_r) >= 85 and max(a_c, a_r) >= 75:
                    return True

        # Fallback: filename completo con artista requerido
        clean_fn = clean_string(filename)
        raw_fn   = clean_string_raw(filename)
        best_t = max(fuzz.token_set_ratio(clean_tit, clean_fn),
                     fuzz.token_set_ratio(raw_tit,   raw_fn))
        best_a = max(fuzz.token_set_ratio(clean_art, clean_fn),
                     fuzz.token_set_ratio(raw_art,   raw_fn))

        if title_words <= 3:
            sort_t = max(fuzz.token_sort_ratio(clean_tit, clean_fn),
                         fuzz.token_sort_ratio(raw_tit,   raw_fn))
            if sort_t >= 85 and best_a >= 75:
                return True
        elif best_t >= 88 and best_a >= 75:
            return True

        full_c = fuzz.token_set_ratio(f"{clean_art} {clean_tit}", clean_fn)
        full_r = fuzz.token_set_ratio(f"{raw_art} {raw_tit}",     raw_fn)
        if max(full_c, full_r) >= 88:
            return True

    # ── RAMA B: Filename SIN separador → matching por título ─────────────────
    else:
        clean_fn = clean_string(filename)
        raw_fn   = clean_string_raw(filename)
        fn_xc    = _strip_quality(clean_fn)
        fn_xr    = _strip_quality(raw_fn)

        # Patrón "ARTISTA _Titulo_ (tipo)": artista al inicio, título entre guiones bajos
        # Detectar: si el artista aparece en el filename Y el título también → match seguro
        art_in_fn  = max(fuzz.token_set_ratio(clean_art, fn_xc),
                         fuzz.token_set_ratio(raw_art,   fn_xr))
        tit_in_fn  = max(fuzz.partial_ratio(clean_tit, fn_xc),
                         fuzz.partial_ratio(raw_tit,   fn_xr))
        if art_in_fn >= 80 and tit_in_fn >= 90:
            return True

        if title_words == 1:
            # 1 token: ratio directo evita "hurt" ≈ "hurting someone else"
            score = max(fuzz.ratio(clean_tit,            fn_xc),
                        fuzz.ratio(raw_tit,              fn_xr),
                        fuzz.token_sort_ratio(clean_tit, fn_xc),
                        fuzz.token_sort_ratio(raw_tit,   fn_xr))
            return score >= 85

        elif title_words <= 3:
            score = max(fuzz.partial_ratio(clean_tit,    fn_xc),
                        fuzz.partial_ratio(raw_tit,      fn_xr),
                        fuzz.token_sort_ratio(clean_tit, fn_xc),
                        fuzz.token_sort_ratio(raw_tit,   fn_xr))
            return score >= 88

        else:
            score = max(fuzz.partial_ratio(clean_tit,    fn_xc),
                        fuzz.partial_ratio(raw_tit,      fn_xr),
                        fuzz.token_sort_ratio(clean_tit, fn_xc),
                        fuzz.token_sort_ratio(raw_tit,   fn_xr))
            return score >= 85

    return False

_JP_RE = re.compile(r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff\uff00-\uffef]')

def has_japanese(track):
    return bool(_JP_RE.search(track.get('name', '')) or _JP_RE.search(track.get('artist', '')))

def smart_compare(playlist_id, start_offset=0, max_tracks=None, skip_japanese=False):
    config = load_config()
    blacklist = load_blacklist()

    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')

    open_live_log_window(COMPARE_LOG_PATH)
    sys.stdout = TeeLogger(COMPARE_LOG_PATH)

    spotify = SpotifyClient(config['spotify_client_id'], config['spotify_client_secret'])

    print(f"Fetching Spotify playlist starting from offset {start_offset}...")
    tracks = []
    offset = start_offset
    limit = 50

    while True:
        chunk = spotify.get_playlist_tracks(playlist_id, offset=offset, limit=limit)
        if not chunk: break
        tracks.extend(chunk)
        offset += limit
        print(f"Fetched {len(tracks)} tracks (total processed: {offset})...", end='\r')
        if max_tracks and len(tracks) >= max_tracks: break
        if len(chunk) < limit: break

    if max_tracks:
        tracks = tracks[:max_tracks]

    print(f"\nTotal tracks to analyze: {len(tracks)}")

    print("Fetching phone files...")
    phone_files = get_phone_files()
    print(f"Total Phone files found: {len(phone_files)}")

    missing_tracks = []
    matched_count = 0
    blacklisted_count = 0
    # Para deduplicar: evitar reportar la misma canción dos veces si está repetida en la playlist
    seen_missing = set()

    print("Comparing...")

    for i, track in enumerate(tracks):
        real_index = start_offset + i + 1
        track_name = track['name']
        track_artist = track['artist']

        # Saltar canciones japonesas si se pidió
        if skip_japanese and has_japanese(track):
            blacklisted_count += 1
            continue

        # Saltar si está en la blacklist
        if is_blacklisted(track, blacklist):
            blacklisted_count += 1
            continue

        found = False
        for filename in phone_files:
            if is_fuzzy_match(track, filename):
                found = True
                matched_count += 1
                break

        if not found:
            # Deduplicar: misma canción repetida en la playlist solo se reporta una vez
            dedup_key = (track_name.lower(), track_artist.lower())
            if dedup_key in seen_missing:
                continue
            seen_missing.add(dedup_key)
            track['_real_index'] = real_index
            missing_tracks.append(track)
            print(f"[MISSING] #{real_index} {track_name} - {track_artist}")

    print(f"\nAnalysis Complete.")
    print(f"Matched: {matched_count}")
    print(f"Blacklisted (skipped): {blacklisted_count}")
    print(f"Missing: {len(missing_tracks)}")
    
    # Report generation
    report_path = os.path.join(os.path.dirname(__file__), '..', 'reports', 'informe_inteligente.txt')
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"INFORME DE SINCRONIZACIÓN INTELIGENTE\n")
        f.write(f"=====================================\n")
        f.write(f"Playlist: {playlist_id}\n")
        f.write(f"Offset inicial: {start_offset}\n")
        f.write(f"Tracks analizados: {len(tracks)}\n")
        f.write(f"Coincidencias encontradas: {matched_count}\n")
        f.write(f"En blacklist (omitidas): {blacklisted_count}\n")
        f.write(f"FALTANTES: {len(missing_tracks)}\n\n")
        
        for t in missing_tracks:
            # Usar el índice real guardado
            idx = t['_real_index']
            f.write(f"#{idx}. {t['name']} - {t['artist']}\n")
            # f.write(f"   (Spotify URI: {t.get('uri', 'N/A')})\n")

    print(f"Report saved to {report_path}")

    if isinstance(sys.stdout, TeeLogger):
        sys.stdout.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python smart_compare.py <playlist_id> [offset] [max_tracks] [--skip-japanese]")
        sys.exit(1)

    p_id = sys.argv[1]
    off = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    max_t = int(sys.argv[3]) if len(sys.argv) > 3 else None
    skip_jp = '--skip-japanese' in sys.argv

    smart_compare(p_id, off, max_t, skip_jp)
