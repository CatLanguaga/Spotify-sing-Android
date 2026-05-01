"""
Reintento de las 4 canciones que fallaron en el batch anterior.
"""
import os
import sys
import json
import subprocess
import time
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.append(os.path.abspath("spotify-sync-cli"))
from src.spotify_client import SpotifyClient
from src.downloader import download_audio

CONFIG_PATH = Path.home() / '.spotifytoyoutube' / 'config.json'
PHONE_MUSIC_DIR = "/storage/emulated/0/snaptube/download/Snaptube Audio"
LOCAL_TEMP_DIR = Path("temp_downloads")

RETRY_TRACKS = [
    {'_real_index': 2237, 'name': 'Ponme el Culo en la Cara - Lento Con Gran Espressione', 'artist': 'Berzas'},
    {'_real_index': 2278, 'name': 'El Cumpleaños Del Viento', 'artist': 'Julio Nava'},
    {'_real_index': 2282, 'name': 'El Puente Más Allá de lo Vivido', 'artist': 'Jauría'},
    {'_real_index': 2338, 'name': 'Manolo Ascodás', 'artist': 'The Kagas'},
]

# Import helpers from download_missing
from download_missing import search_best_audio

def load_config():
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

def push_to_phone(local_path):
    remote_path = f"{PHONE_MUSIC_DIR}/{os.path.basename(local_path)}"
    result = subprocess.run(
        ['adb', 'push', local_path, remote_path],
        capture_output=True, text=True, encoding='utf-8', errors='replace'
    )
    return result.returncode == 0, result.stderr

def main():
    config = load_config()
    spotify = SpotifyClient(config['spotify_client_id'], config['spotify_client_secret'])
    LOCAL_TEMP_DIR.mkdir(exist_ok=True)

    for track in RETRY_TRACKS:
        idx = track['_real_index']
        name = track['name']
        artist = track['artist']

        print(f"\n[RETRY] #{idx} {name} - {artist}")

        # Buscar metadata en Spotify
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
                print(f"  -> Spotify: {duration_ms}ms")
        except Exception as e:
            print(f"  -> Spotify error: {e}")

        # Buscar en YouTube con lógica mejorada
        print(f"  -> Buscando en YouTube...", end=' ', flush=True)
        yt_url, score = search_best_audio(name, artist, duration_ms)

        if not yt_url:
            print("NO ENCONTRADO — saltando")
            continue

        print(f"OK (score={score})")
        print(f"  -> URL: {yt_url}")

        # Descargar
        print(f"  -> Descargando...")
        ok, msg, local_path = download_audio(yt_url, str(LOCAL_TEMP_DIR), track)

        if not ok:
            print(f"  -> FALLO: {msg}")
            continue

        # Push al telefono
        print(f"  -> Enviando al telefono...")
        pushed, err = push_to_phone(local_path)

        if not pushed:
            print(f"  -> FALLO ADB: {err}")
            continue

        try:
            os.remove(local_path)
        except:
            pass

        print(f"  -> ✓ Sincronizado!")
        time.sleep(2)  # Pausa extra para evitar rate-limit

    print("\nRetry completado.")

if __name__ == "__main__":
    main()
