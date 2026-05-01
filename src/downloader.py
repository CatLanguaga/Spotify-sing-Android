"""
YouTube audio downloader with full metadata embedding
Uses pytubefix for download and video info
"""
import os
import requests
from pathlib import Path


def download_audio(youtube_url, output_folder, track_info=None):
    """
    Download audio from YouTube and embed metadata
    Uses YouTube thumbnail as fallback if no Spotify album art
    """
    try:
        from pytubefix import YouTube
        
        Path(output_folder).mkdir(parents=True, exist_ok=True)
        
        yt = YouTube(youtube_url)
        
        # Get audio stream
        audio_stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()
        
        if not audio_stream:
            return False, "No audio stream", None
        
        # Create filename
        if track_info:
            artist = track_info.get('artist', 'Unknown')
            name = track_info.get('name', 'Unknown')
            safe_artist = "".join(c for c in artist if c.isalnum() or c in ' ._-').strip()[:50]
            safe_name = "".join(c for c in name if c.isalnum() or c in ' ._-').strip()[:50]
            filename = f"{safe_artist} - {safe_name}"
        else:
            filename = "".join(c for c in yt.title if c.isalnum() or c in ' ._-').strip()[:80]
        
        # Download raw audio (aac/webm/etc)
        temp_path = audio_stream.download(output_path=output_folder, filename=f"{filename}.mp4")
        
        # Convert to real MP3 using ffmpeg
        final_path = os.path.join(output_folder, f"{filename}.mp3")
        if os.path.exists(final_path):
            os.remove(final_path)
        
        import subprocess as _sp
        ffmpeg_result = _sp.run(
            ['ffmpeg', '-y', '-i', temp_path, '-vn', '-acodec', 'libmp3lame', '-q:a', '0', final_path],
            capture_output=True, text=True
        )
        
        # Remove raw download regardless of outcome
        try:
            os.remove(temp_path)
        except Exception:
            pass
        
        if ffmpeg_result.returncode != 0 or not os.path.exists(final_path):
            return False, f"ffmpeg conversion failed: {ffmpeg_result.stderr[-200:]}", None
        
        # Get YouTube thumbnail as fallback
        youtube_thumbnail = yt.thumbnail_url
        
        # Add metadata
        if track_info:
            # Use YouTube thumbnail if no Spotify art
            if not track_info.get('album_art_url') and youtube_thumbnail:
                track_info['album_art_url'] = youtube_thumbnail
            
            add_metadata(final_path, track_info)
        else:
            # Create basic metadata from YouTube info
            yt_info = {
                'name': yt.title,
                'artist': yt.author,
                'album_art_url': youtube_thumbnail
            }
            add_metadata(final_path, yt_info)
        
        return True, "OK", final_path
        
    except Exception as e:
        error_msg = str(e)
        if "regex_search" in error_msg:
            return False, "Video no disponible", None
        elif "403" in error_msg:
            return False, "Restringido", None
        else:
            return False, error_msg[:30], None


def add_metadata(filepath, track_info):
    """Add ID3 metadata to MP3 file"""
    try:
        from mutagen.mp3 import MP3
        from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TRCK, APIC, ID3NoHeaderError
        
        try:
            audio = MP3(filepath, ID3=ID3)
        except ID3NoHeaderError:
            audio = MP3(filepath)
            audio.add_tags()
        
        # Clear existing tags
        for tag in ['TIT2', 'TPE1', 'TALB', 'TDRC', 'TRCK', 'APIC']:
            try:
                audio.tags.delall(tag)
            except:
                pass
        
        # Add title
        if track_info.get('name'):
            audio.tags.add(TIT2(encoding=3, text=track_info['name']))
        
        # Add artist
        if track_info.get('all_artists'):
            audio.tags.add(TPE1(encoding=3, text=track_info['all_artists']))
        elif track_info.get('artist'):
            audio.tags.add(TPE1(encoding=3, text=track_info['artist']))
        
        # Add album
        if track_info.get('album'):
            audio.tags.add(TALB(encoding=3, text=track_info['album']))
        
        # Add year
        if track_info.get('year'):
            audio.tags.add(TDRC(encoding=3, text=track_info['year']))
        
        # Add track number
        if track_info.get('track_number'):
            audio.tags.add(TRCK(encoding=3, text=str(track_info['track_number'])))
        
        # Download and add cover art (Spotify or YouTube)
        if track_info.get('album_art_url'):
            try:
                response = requests.get(track_info['album_art_url'], timeout=10)
                if response.status_code == 200:
                    # Detect image type
                    mime = 'image/jpeg'
                    if 'png' in track_info['album_art_url'].lower():
                        mime = 'image/png'
                    elif 'webp' in track_info['album_art_url'].lower():
                        mime = 'image/webp'
                    
                    audio.tags.add(APIC(
                        encoding=3,
                        mime=mime,
                        type=3,  # Cover (front)
                        desc='Cover',
                        data=response.content
                    ))
            except Exception as e:
                print(f"Could not download cover art: {e}")
        
        audio.save()
        return True
        
    except Exception as e:
        print(f"Error adding metadata: {e}")
        return False
