import sys
import os
from pathlib import Path
import json
import subprocess
import re
from unidecode import unidecode
from thefuzz import fuzz

# Add spotify-sync-cli to path
sys.path.append(os.path.abspath("spotify-sync-cli"))
from src.spotify_client import SpotifyClient

CONFIG_PATH = Path.home() / '.spotifytoyoutube' / 'config.json'
PHONE_MUSIC_DIR = "/storage/emulated/0/snaptube/download/Snaptube Audio"

def load_config():
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

def clean_string_raw(s):
    if not s: return ""
    s = s.lower()
    s = re.sub(r'\.(mp3|m4a|flac|wav)$', '', s)
    # Keep it simple for debug
    return " ".join(s.split())

def check_specific_song():
    config = load_config()
    spotify = SpotifyClient(config['spotify_client_id'], config['spotify_client_secret'])
    
    # Force UTF-8 output for Windows console
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')
    
    # We suspect the song is around offset 2070 relative to the start (or absolute index)
    # The user started compare at 1900.
    # User sees 2074. My script saw 2076/2077.
    # The song "Rewrite" (リライト) should be there.
    
    # Let's fetch a chunk around there.
    # Since offset 1900 + 170 approx = 2070.
    
    print("Fetching tracks around index 2070...")
    offset = 2060
    limit = 30
    tracks = spotify.get_playlist_tracks('21oT9wIPYxoN6zMeEjsqgZ', offset=offset, limit=limit)
    
    target_song = None
    print(f"Found {len(tracks)} tracks from offset {offset}:")
    for i, track in enumerate(tracks):
        idx = offset + i + 1
        print(f"#{idx}: {track['name']} - {track['artist']}")
        if "リライト" in track['name'] or "Rewrite" in track['name']:
            target_song = track
            print(f"--> FOUND TARGET at #{idx}")

    if not target_song:
        print("\n❌ Could not find 'Rewrite' / 'リライト' in this range.")
        return

    print("\nChecking phone files for matches...")
    cmd = ['adb', 'shell', 'ls', '-1', f'"{PHONE_MUSIC_DIR}"']
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    files = result.stdout.strip().split('\n')
    
    candidates = []
    
    track_name = target_song['name']
    track_artist = target_song['artist']
    
    print(f"Looking for: {track_name} - {track_artist}")
    
    for f in files:
        f = f.strip()
        if not f: continue
        
        # Check fuzzy match
        # Logic from smart_compare
        
        clean_fn = unidecode(f.lower())
        clean_tit = unidecode(track_name.lower())
        
        raw_fn = clean_string_raw(f)
        raw_tit = clean_string_raw(track_name)
        
        score_clean = fuzz.token_set_ratio(clean_tit, clean_fn)
        score_raw = fuzz.token_set_ratio(raw_tit, raw_fn)
        
        best_score = max(score_clean, score_raw)
        
        if best_score > 50: # Low threshold to see what it *might* be matching
            candidates.append((f, best_score))

    candidates.sort(key=lambda x: x[1], reverse=True)
    
    print("\nTop Matches found on phone:")
    for c in candidates[:10]:
        print(f"Score {c[1]}: {c[0]}")

if __name__ == "__main__":
    check_specific_song()
