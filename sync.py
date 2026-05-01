import os
import sys
import json
import subprocess
import time
from pathlib import Path

# Force UTF-8 output for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Add current directory to path so we can import src modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.spotify_client import SpotifyClient
from src.youtube_client import YouTubeClient
from src.downloader import download_audio

# Configuration
CONFIG_PATH = Path.home() / '.spotifytoyoutube' / 'config.json'
PHONE_MUSIC_DIR = "/storage/emulated/0/snaptube/download/Snaptube Audio"
LOCAL_TEMP_DIR = Path("temp_downloads")

def load_config():
    if not CONFIG_PATH.exists():
        print(f"Error: Config file not found at {CONFIG_PATH}")
        return None
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

def check_adb():
    """Check if ADB is available and a device is connected"""
    try:
        result = subprocess.run(['adb', 'devices'], capture_output=True, text=True, encoding='utf-8', errors='replace')
        if result.returncode != 0:
            print("Error running adb devices")
            return False
        
        lines = result.stdout.strip().split('\n')
        if len(lines) < 2:
            print("No devices found. Connect your phone via USB and enable USB Debugging.")
            return False
            
        devices = [line for line in lines[1:] if line.strip() and 'device' in line]
        if not devices:
            print("No authorized devices found. Check your phone screen for RSA prompt.")
            return False
            
        print(f"Connected to: {devices[0].split()[0]}")
        return True
    except FileNotFoundError:
        print("ADB not found in PATH. Please install Android Platform Tools.")
        return False

def get_phone_files():
    """List files in the phone music directory"""
    try:
        # Create directory if it doesn't exist
        # Quote path for ADB shell to handle spaces
        subprocess.run(['adb', 'shell', 'mkdir', '-p', f'"{PHONE_MUSIC_DIR}"'], check=True, encoding='utf-8', errors='replace')
        
        # List files
        result = subprocess.run(['adb', 'shell', 'ls', f'"{PHONE_MUSIC_DIR}"'], capture_output=True, text=True, encoding='utf-8', errors='replace')
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

def sync_playlist(playlist_id, dry_run=False):
    config = load_config()
    if not config:
        return

    if not check_adb():
        return

    print("Connecting to Spotify...")
    spotify = SpotifyClient(config['spotify_client_id'], config['spotify_client_secret'])
    youtube = YouTubeClient()

    print(f"Fetching playlist {playlist_id}...")
    # Fetch all tracks (pagination needed)
    tracks = []
    offset = 0
    limit = 50
    
    while True:
        chunk = spotify.get_playlist_tracks(playlist_id, offset=offset, limit=limit)
        if not chunk:
            break
        tracks.extend(chunk)
        offset += limit
        print(f"Fetched {len(tracks)} tracks...", end='\r')
        if len(chunk) < limit:
            break
    
    print(f"\nTotal tracks found: {len(tracks)}")

    print("Checking phone storage...")
    phone_files = get_phone_files()
    print(f"Found {len(phone_files)} existing songs on phone.")

    # Prepare for download
    LOCAL_TEMP_DIR.mkdir(exist_ok=True)
    
    download_queue = []
    
    for track in tracks:
        artist = track['artist']
        name = track['name']
        
        # Construct expected filename (simulating downloader logic)
        safe_artist = sanitize_filename(artist)[:50]
        safe_name = sanitize_filename(name)[:50]
        expected_filename = f"{safe_artist} - {safe_name}.mp3"
        
        # Check if exists on phone (loose check)
        # We check if expected_filename is in phone_files
        # This is basic; exact match required. 
        if expected_filename in phone_files:
            continue
            
        download_queue.append((track, expected_filename))

    print(f"Songs to sync: {len(download_queue)}")

    if dry_run:
        print("\n[ANALYSIS MODE] The following songs are missing on the device:")
        for i, (track, fname) in enumerate(download_queue):
            print(f"{i+1}. {track['name']} - {track['artist']} (File: {fname})")
        print("\nRun without --check to download them.")
        return

    if not download_queue:
        print("All synced! 😼")
        return

    for i, (track, filename) in enumerate(download_queue):
        print(f"[{i+1}/{len(download_queue)}] Processing: {track['name']} - {track['artist']}")
        
        # 1. Search YouTube
        yt_url = youtube.search_song(track['name'], track['artist'], track['duration_ms'])
        if not yt_url:
            print("  -> Not found on YouTube, skipping.")
            continue

        # 2. Download locally
        print("  -> Downloading...")
        success, msg, local_path = download_audio(yt_url, str(LOCAL_TEMP_DIR), track)
        
        if not success:
            print(f"  -> Download failed: {msg}")
            continue

        # 3. Push to phone
        print("  -> Pushing to phone...")
        try:
            # ADB push
            remote_path = f"{PHONE_MUSIC_DIR}/{os.path.basename(local_path)}"
            subprocess.run(['adb', 'push', local_path, remote_path], check=True, capture_output=True)
            print("  -> Synced!")
            
            # 4. Clean up local
            os.remove(local_path)
            
        except subprocess.CalledProcessError as e:
            print(f"  -> ADB Push failed: {e}")

    # Cleanup temp dir
    try:
        os.rmdir(LOCAL_TEMP_DIR)
    except:
        pass

    print("Sync complete! 🎧")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Sync Spotify playlist to Android device')
    parser.add_argument('playlist_url', nargs='?', help='Spotify playlist URL or ID')
    parser.add_argument('--check', action='store_true', help='Only check for missing songs, do not download')
    
    args = parser.parse_args()
    
    if not args.playlist_url:
        print("Usage: python sync.py <playlist_id_or_url> [--check]")
        sys.exit(1)
        
    playlist_arg = args.playlist_url
    if 'playlist/' in playlist_arg:
        playlist_id = playlist_arg.split('playlist/')[1].split('?')[0]
    else:
        playlist_id = playlist_arg
        
    sync_playlist(playlist_id, dry_run=args.check)
