import os
import sys
import json
import subprocess
from pathlib import Path

# Add spotify-sync-cli to path
sys.path.append(os.path.abspath("spotify-sync-cli"))

from src.spotify_client import SpotifyClient

CONFIG_PATH = Path.home() / '.spotifytoyoutube' / 'config.json'
PHONE_MUSIC_DIR = "/storage/emulated/0/snaptube/download/Snaptube Audio"

def load_config():
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

def get_phone_files():
    """List files in the phone music directory"""
    try:
        # Quote path for ADB shell to handle spaces
        # Using -1 to list one file per line, no extra info
        cmd = ['adb', 'shell', 'ls', '-1', f'"{PHONE_MUSIC_DIR}"']
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
        
        if result.returncode != 0:
            print("Error listing phone files")
            return []
            
        files = result.stdout.strip().split('\n')
        return [f.strip() for f in files if f.strip().endswith('.mp3')]
    except Exception as e:
        print(f"Error accessing phone: {e}")
        return []

def sanitize_filename(name):
    """Basic sanitization matching downloader logic roughly"""
    return "".join(c for c in name if c.isalnum() or c in ' ._-').strip()

def generate_report(playlist_id):
    config = load_config()
    spotify = SpotifyClient(config['spotify_client_id'], config['spotify_client_secret'])

    print("Fetching Spotify playlist...")
    tracks = []
    offset = 0
    limit = 50
    while True:
        chunk = spotify.get_playlist_tracks(playlist_id, offset=offset, limit=limit)
        if not chunk: break
        tracks.extend(chunk)
        offset += limit
        print(f"Fetched {len(tracks)} tracks...", end='\r')
        if len(chunk) < limit: break
    
    print(f"\nTotal Spotify tracks: {len(tracks)}")

    print("Fetching phone files...")
    phone_files = get_phone_files()
    print(f"Total Phone files: {len(phone_files)}")
    
    # Normalize phone filenames for comparison (remove extension, lowercase)
    # This is tricky because naming conventions might differ.
    # The sync script expects: "{safe_artist} - {safe_name}.mp3"
    
    missing_tracks = []
    
    for track in tracks:
        artist = track['artist']
        name = track['name']
        
        safe_artist = sanitize_filename(artist)[:50]
        safe_name = sanitize_filename(name)[:50]
        expected_filename = f"{safe_artist} - {safe_name}.mp3"
        
        if expected_filename not in phone_files:
            missing_tracks.append({
                'artist': artist,
                'name': name,
                'expected_file': expected_filename
            })

    report_path = "informe_faltantes.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"INFORME DE SINCRONIZACIÓN SPOTIFY\n")
        f.write(f"=================================\n")
        f.write(f"Playlist: {playlist_id}\n")
        f.write(f"Total en Spotify: {len(tracks)}\n")
        f.write(f"Total en Teléfono: {len(phone_files)}\n")
        f.write(f"Faltantes en Teléfono: {len(missing_tracks)}\n\n")
        f.write("CANCIONES FALTANTES:\n")
        f.write("====================\n")
        
        for i, t in enumerate(missing_tracks):
            f.write(f"{i+1}. {t['name']} - {t['artist']}\n")
            # f.write(f"   (Archivo esperado: {t['expected_file']})\n")
    
    print(f"\nReport generated: {report_path}")
    print(f"Missing songs: {len(missing_tracks)}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Need playlist ID")
        sys.exit(1)
    generate_report(sys.argv[1])
