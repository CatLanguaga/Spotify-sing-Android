"""
Descarga las canciones del informe_inteligente.txt que faltan en el telefono.
- Salta las canciones excluidas manualmente
- Prefiere audio puro sobre videoclips oficiales o en vivo
- Push directo a ADB
"""
import os
import sys
import re
import json
import subprocess
import time
from pathlib import Path

# Force UTF-8
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.spotify_client import SpotifyClient
from src.downloader import download_audio

try:
    from pytubefix import Search, YouTube
except ImportError:
    print("ERROR: pytubefix no instalado.")
    sys.exit(1)

from thefuzz import fuzz
from unidecode import unidecode

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
        f'start "Log en vivo - Descarga" cmd /k powershell -NoExit -Command "Get-Content -Path \'{log_path}\' -Wait"',
        shell=True
    )
    time.sleep(0.5)

# ─── CONFIG ────────────────────────────────────────────────────────────────────
CONFIG_PATH = Path.home() / '.spotifytoyoutube' / 'config.json'
PHONE_MUSIC_DIR = "/storage/emulated/0/snaptube/download/Snaptube Audio"
_ROOT = Path(__file__).parent.parent
LOCAL_TEMP_DIR = _ROOT / "temp_downloads"
REPORT_PATH = _ROOT / "reports" / "informe_inteligente.txt"
LOG_PATH = _ROOT / "reports" / "download_log.txt"

# Indices a SALTAR (posicion real en playlist, ya estan en el telefono)
SKIP_INDICES = {1914, 2218, 2142, 2222, 2266}

# Terminos que indican que un video es MV/Live (penalizar)
# NOTA: lyric videos (oficiales y de fans) son VÁLIDOS — buena calidad de audio
BAD_TERMS = [
    "official music video", "official video", "music video",
    "video oficial", "videoclip",
    " mv",          # " mv" con espacio para no pillar "remove" etc.
    "live at", "live from", "live in", "live concert",
    "concert", "en vivo", "live performance",
]

# Terminos que indican BUEN audio (bonus positivo)
GOOD_TERMS = [
    "audio", "official audio", "audio oficial",
    "hq", "hd audio", "high quality", "320", "lossless",
    "topic",        # canales "- Topic" de YouTube Music = audio limpio
    "lyric video", "lyrics video", "letra", "letras",   # lyrics = buena fuente
    "lyric", "lyrics",
]
# ───────────────────────────────────────────────────────────────────────────────


def load_config():
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)


def parse_report(report_path):
    """Parsea el informe y devuelve lista de (index, name, artist)"""
    tracks = []
    pattern = re.compile(r'^#(\d+)\.\s+(.+?)\s+-\s+(.+)$')
    with open(report_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            m = pattern.match(line)
            if m:
                idx = int(m.group(1))
                name = m.group(2).strip()
                artist = m.group(3).strip()
                tracks.append({'_real_index': idx, 'name': name, 'artist': artist})
    return tracks


def score_video(video, song_name, artist, expected_duration_sec):
    """
    Puntua un video de YouTube.
    Primero filtra por relevancia (el video debe ser la canción buscada).
    Luego premia audio limpio y penaliza MVs/lives.
    """
    title_lower = (video.title or "").lower()
    author_lower = (video.author or "").lower()

    vt = unidecode(title_lower)
    sn = unidecode(song_name.lower())
    ar = unidecode(artist.lower())

    # ── FILTRO DURO DE RELEVANCIA ────────────────────────────────────────────
    title_rel = max(fuzz.partial_ratio(sn, vt),
                    fuzz.token_set_ratio(sn, vt))
    if title_rel < 60:
        return -9999  # Descarte: el video no menciona esta canción

    # El artista debe aparecer en el título o canal del video.
    # Usar palabras literales (len > 3) para evitar falsos positivos por similitud
    # de caracteres entre nombres completamente distintos ("NIN Channel" ≈ "Johnny Cash").
    al_clean = unidecode(author_lower)
    ar_words = [w for w in ar.split() if len(w) > 3]
    if ar_words:
        # Al menos una palabra clave del artista debe aparecer en título o canal
        word_found = any(w in vt or w in al_clean for w in ar_words)
        # O el nombre completo del artista debe coincidir bien con el canal (VEVO, Topic, etc.)
        channel_match = fuzz.ratio(ar, al_clean) >= 60
        artist_confirmed = word_found or channel_match
    else:
        # Artista con nombre muy corto (ej: "lol", "Shé") → fallback fuzzy
        artist_confirmed = max(fuzz.partial_ratio(ar, vt), fuzz.ratio(ar, al_clean)) >= 45

    if not artist_confirmed:
        return -9999  # Descarte: artista completamente ausente del video

    # Score numérico de artista para bonificaciones
    artist_rel = max(fuzz.partial_ratio(ar, vt), fuzz.token_set_ratio(ar, vt),
                     fuzz.ratio(ar, al_clean))

    score = 100

    # ── RELEVANCIA POSITIVA ──────────────────────────────────────────────────
    if title_rel >= 90:
        score += 40
    elif title_rel >= 75:
        score += 20

    if artist_rel >= 80:
        score += 30
    elif artist_rel >= 60:
        score += 15

    # Penalización adicional si el artista está presente pero débil (45-59)
    if artist_rel < 60:
        score -= 20

    # ── CALIDAD DE AUDIO ─────────────────────────────────────────────────────
    for bad in BAD_TERMS:
        if bad in title_lower:
            score -= 40
            break

    for good in GOOD_TERMS:
        if good in title_lower or good in author_lower:
            score += 30
            break

    # Canal "- Topic" de YouTube Music = audio puro garantizado
    if "topic" in author_lower:
        score += 50

    if "lyric" in title_lower or "letra" in title_lower:
        score += 20

    # ── DURACIÓN ─────────────────────────────────────────────────────────────
    if video.length is not None and expected_duration_sec is not None:
        diff = abs(video.length - expected_duration_sec)
        if diff <= 10:
            score += 30
        elif diff <= 20:
            score += 15
        elif diff <= 40:
            score += 5
        else:
            score -= 20

    return score


def search_best_audio(song_name, artist, duration_ms, max_results=15):
    """Busca el mejor audio en YouTube verificando relevancia y evitando MVs/lives."""
    expected_sec = duration_ms / 1000 if duration_ms else None

    queries = [
        f"{song_name} {artist} official audio",
        f"{song_name} {artist} audio",
        f"{song_name} {artist} lyric video",
        f"{song_name} {artist} lyrics",
        f"{song_name} {artist}",
    ]

    best_url = None
    best_score = -9999
    best_title = None
    seen_ids = set()

    for query in queries:
        try:
            search = Search(query)
            results = search.videos[:max_results] if search.videos else []
        except Exception as e:
            print(f"  -> Search error: {e}")
            continue

        for video in results:
            vid_id = getattr(video, 'video_id', None)
            if not vid_id or vid_id in seen_ids:
                continue
            seen_ids.add(vid_id)

            try:
                s = score_video(video, song_name, artist, expected_sec)
                if s > best_score:
                    best_score = s
                    best_url = f"https://www.youtube.com/watch?v={vid_id}"
                    best_title = video.title
            except Exception:
                continue

        # Umbral alto: solo cortar si tenemos relevancia + buena calidad confirmada
        if best_score >= 200:
            break

    return best_url, best_score, best_title


def get_spotify_duration(spotify_client, track_name, artist_name):
    """Intenta obtener la duracion real de Spotify para un track."""
    try:
        results = spotify_client.search_track(track_name, artist_name)
        if results and len(results) > 0:
            return results[0].get('duration_ms')
    except Exception:
        pass
    return None


def push_to_phone(local_path):
    remote_path = f"{PHONE_MUSIC_DIR}/{os.path.basename(local_path)}"
    result = subprocess.run(
        ['adb', 'push', local_path, remote_path],
        capture_output=True, text=True, encoding='utf-8', errors='replace'
    )
    return result.returncode == 0, result.stderr


def main(fmt='mp3', quality=320, output_dir=None):
    """
    Args:
        fmt:        Output audio format — 'mp3', 'm4a', or 'opus'
        quality:    Target bitrate in kbps — 128, 192, or 320
        output_dir: Local temp folder for downloads (overrides LOCAL_TEMP_DIR)
    """
    config = load_config()

    open_live_log_window(LOG_PATH)
    sys.stdout = TeeLogger(LOG_PATH)

    temp_dir = Path(output_dir) if output_dir else LOCAL_TEMP_DIR
    print(f"Formato: {fmt} | Calidad: {quality}kbps | Carpeta temporal: {temp_dir}")

    spotify = SpotifyClient(config['spotify_client_id'], config['spotify_client_secret'])

    print("Parseando informe...")
    all_tracks = parse_report(REPORT_PATH)
    print(f"Total en informe: {len(all_tracks)}")

    # Filtrar los que hay que saltar
    tracks = [t for t in all_tracks if t['_real_index'] not in SKIP_INDICES]
    skipped = [t for t in all_tracks if t['_real_index'] in SKIP_INDICES]

    print(f"Saltando {len(skipped)} canciones ya en el telefono: {[t['_real_index'] for t in skipped]}")
    print(f"A descargar: {len(tracks)} canciones")
    print()

    temp_dir.mkdir(parents=True, exist_ok=True)

    failed = []
    success_count = 0

    print("DOWNLOAD LOG\n============\n")

    for i, track in enumerate(tracks):
        idx = track['_real_index']
        name = track['name']
        artist = track['artist']

        print(f"[{i+1}/{len(tracks)}] #{idx} {name} - {artist}")

        # Buscar duracion en Spotify (para mejor matching de duracion en YT)
        duration_ms = None
        try:
            results = spotify.search_track(name, artist)
            if results:
                duration_ms = results[0].get('duration_ms')
                track['duration_ms'] = duration_ms
                track['album_art_url'] = results[0].get('album_art_url')
                track['album'] = results[0].get('album')
                track['year'] = results[0].get('year')
                track['track_number'] = results[0].get('track_number')
                track['all_artists'] = results[0].get('all_artists', artist)
        except Exception as e:
            print(f"  -> Spotify search error: {e}")

        # Buscar mejor audio en YouTube
        print(f"  -> Buscando en YouTube...", end=' ', flush=True)
        yt_url, score, yt_title = search_best_audio(name, artist, duration_ms)

        if not yt_url or score < 0:
            print(f"NO ENCONTRADO")
            print(f"SKIP (no YT) | #{idx} {name} - {artist}")
            failed.append({'idx': idx, 'name': name, 'artist': artist, 'reason': 'No encontrado en YouTube'})
            continue

        print(f"OK (score={score})")
        print(f"  -> YT: {yt_title}")

        # Descargar
        print(f"  -> Descargando...")
        ok, msg, local_path = download_audio(yt_url, str(temp_dir), track, fmt=fmt, quality=quality)

        if not ok:
            print(f"  -> FALLO descarga: {msg}")
            print(f"FAIL (dl) | #{idx} {name} - {artist} | {msg}")
            failed.append({'idx': idx, 'name': name, 'artist': artist, 'reason': f'Download: {msg}'})
            continue

        # Push a telefono
        print(f"  -> Enviando al telefono...")
        pushed, err = push_to_phone(local_path)

        if not pushed:
            print(f"  -> FALLO ADB push: {err}")
            print(f"FAIL (adb) | #{idx} {name} - {artist} | {err}")
            failed.append({'idx': idx, 'name': name, 'artist': artist, 'reason': f'ADB: {err}'})
            # Dejar archivo local para reintento manual
            continue

        # Limpiar archivo local
        try:
            os.remove(local_path)
        except Exception:
            pass

        print(f"  -> OK | #{idx} {name} - {artist} | YT: {yt_title}")
        success_count += 1

        # Pausa breve para no saturar YT
        time.sleep(1)

    # Resumen final
    print(f"\n{'='*50}")
    print(f"COMPLETADO")
    print(f"  Exitosas : {success_count}")
    print(f"  Fallidas : {len(failed)}")
    print(f"  Saltadas : {len(skipped)}")
    print(f"  Log en   : {LOG_PATH}")

    if failed:
        print(f"\nCANCIONES QUE FALLARON:")
        for f in failed:
            print(f"  #{f['idx']} {f['name']} - {f['artist']} ({f['reason']})")

    if isinstance(sys.stdout, TeeLogger):
        sys.stdout.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Download missing tracks from the compare report")
    parser.add_argument('--format', dest='fmt', choices=['mp3', 'm4a', 'opus'], default='mp3')
    parser.add_argument('--quality', type=int, choices=[128, 192, 320], default=320)
    parser.add_argument('--output-dir', default=None)
    _args = parser.parse_args()
    main(fmt=_args.fmt, quality=_args.quality, output_dir=_args.output_dir)
