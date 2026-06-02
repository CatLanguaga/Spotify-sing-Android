"""
YouTube audio downloader with full metadata embedding
Uses pytubefix for download and video info
"""
import os
import requests
import shutil
import subprocess
import threading
import unicodedata
from pathlib import Path
from typing import Callable, Optional

from src.youtube_client import without_env_proxies

_WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}

_KEY_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
_MAJOR_PROFILE = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
_MINOR_PROFILE = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]


def _sanitize_filename_part(value: str, fallback: str, max_chars: int = 80) -> str:
    """Keep Unicode letters/numbers, remove unsafe symbols, controls and emoji."""
    normalized = unicodedata.normalize("NFC", value or "")
    chars: list[str] = []
    for ch in normalized:
        category = unicodedata.category(ch)
        if category[0] in {"L", "M", "N"} or ch in " ._-'()[]":
            chars.append(ch)
        elif category[0] in {"C", "S"}:
            chars.append("_")
        else:
            chars.append("_")

    cleaned = "".join(chars)
    cleaned = " ".join(cleaned.split()).strip(" ._-")
    if not cleaned:
        cleaned = fallback
    if cleaned.upper() in _WINDOWS_RESERVED_NAMES:
        cleaned = f"{cleaned}_"
    return cleaned[:max_chars].strip(" ._-") or fallback


def _unique_path(folder: Path, stem: str, suffix: str) -> Path:
    candidate = folder / f"{stem}{suffix}"
    n = 1
    while candidate.exists():
        candidate = folder / f"{stem} ({n}){suffix}"
        n += 1
    return candidate


def _estimate_audio_metadata(filepath: str) -> dict:
    """Best-effort BPM/key analysis. Missing librosa never blocks downloads."""
    try:
        import librosa
        import numpy as np

        y, sr = librosa.load(filepath, mono=True, duration=180)
        if y.size == 0:
            return {}

        tempo, _beats = librosa.beat.beat_track(y=y, sr=sr)
        if hasattr(tempo, "__len__"):
            tempo = float(tempo[0])
        bpm = int(round(float(tempo))) if tempo else None

        chroma = librosa.feature.chroma_stft(y=y, sr=sr)
        chroma_mean = chroma.mean(axis=1)
        if not np.any(chroma_mean):
            return {"bpm": bpm} if bpm else {}

        major_scores = [
            float(np.corrcoef(chroma_mean, np.roll(_MAJOR_PROFILE, i))[0, 1])
            for i in range(12)
        ]
        minor_scores = [
            float(np.corrcoef(chroma_mean, np.roll(_MINOR_PROFILE, i))[0, 1])
            for i in range(12)
        ]
        major_idx = int(np.nanargmax(major_scores))
        minor_idx = int(np.nanargmax(minor_scores))
        if major_scores[major_idx] >= minor_scores[minor_idx]:
            key = f"{_KEY_NAMES[major_idx]} major"
        else:
            key = f"{_KEY_NAMES[minor_idx]} minor"

        result = {}
        if bpm:
            result["bpm"] = bpm
        if key:
            result["key"] = key
        return result
    except Exception:
        return {}


def find_ffmpeg():
    env_path = os.environ.get("FFMPEG_PATH")
    if env_path and Path(env_path).is_file():
        return env_path

    path_match = shutil.which("ffmpeg")
    if path_match:
        return path_match

    candidates = [
        *(
            Path.home()
            / "AppData"
            / "Local"
            / "Microsoft"
            / "WinGet"
            / "Packages"
        ).glob("Gyan.FFmpeg*/**/bin/ffmpeg.exe"),
        Path("C:/ProgramData/chocolatey/bin/ffmpeg.exe"),
        Path("C:/Program Files/ffmpeg/bin/ffmpeg.exe"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)

    return None


def download_audio(
    youtube_url,
    output_folder,
    track_info=None,
    fmt='mp3',
    quality=320,
    on_progress: Optional[Callable[[int], None]] = None,
):
    """
    Download audio from YouTube and embed metadata.

    Args:
        fmt:         Output format — 'mp3', 'm4a', or 'opus'
        quality:     Target bitrate in kbps — 128, 192, or 320
        on_progress: Optional callback(percent: int 0-100) called during download + conversion
    """
    _CODEC = {'mp3': 'libmp3lame', 'm4a': 'aac', 'opus': 'libopus'}
    codec = _CODEC.get(fmt, 'libmp3lame')
    ext = fmt
    ffmpeg_bin = find_ffmpeg()
    if not ffmpeg_bin:
        return False, "ffmpeg not found", None

    try:
        from pytubefix import YouTube

        Path(output_folder).mkdir(parents=True, exist_ok=True)

        with without_env_proxies():
            yt = YouTube(youtube_url)

        if on_progress:
            _total = [0]

            def _yt_cb(stream, chunk, bytes_remaining):
                total = _total[0] or getattr(stream, 'filesize', 0)
                if not _total[0] and total:
                    _total[0] = total
                if total > 0:
                    pct = int((1 - bytes_remaining / total) * 60)  # 0-60
                    on_progress(5 + pct)  # reports 5-65%

            yt.register_on_progress_callback(_yt_cb)

        audio_stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()

        if not audio_stream:
            return False, "No audio stream", None

        if track_info:
            artist = _sanitize_filename_part(track_info.get('artist', 'Unknown'), 'Unknown', 50)
            name = _sanitize_filename_part(track_info.get('name', 'Unknown'), 'Unknown', 70)
            filename = f"{artist} - {name}"
        else:
            filename = _sanitize_filename_part(yt.title, 'track', 100)

        out_dir = Path(output_folder)
        final_path_obj = _unique_path(out_dir, filename, f".{ext}")
        source_path_obj = _unique_path(out_dir, f"{final_path_obj.stem}__source", ".mp4")

        with without_env_proxies():
            temp_path = audio_stream.download(
                output_path=output_folder,
                filename=source_path_obj.name,
                skip_existing=True,
                max_retries=2,
            )

        if on_progress:
            on_progress(65)

        final_path = str(final_path_obj)

        if on_progress:
            # Use Popen + -progress pipe:1 for granular ffmpeg progress
            duration_us = (getattr(yt, 'length', 0) or 0) * 1_000_000
            stderr_buf: list[str] = []

            proc = subprocess.Popen(
                [ffmpeg_bin, '-y', '-i', temp_path, '-vn', '-acodec', codec,
                 '-b:a', f'{quality}k', '-loglevel', 'error', '-progress', 'pipe:1', final_path],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )

            def _drain_stderr():
                for line in proc.stderr:
                    stderr_buf.append(line)

            t = threading.Thread(target=_drain_stderr, daemon=True)
            t.start()

            for line in proc.stdout:
                line = line.strip()
                if line.startswith('out_time_us=') and duration_us > 0:
                    try:
                        us = int(line.split('=', 1)[1])
                        pct = min(100, int(us / duration_us * 100))
                        on_progress(65 + int(pct * 0.30))  # reports 65-95%
                    except (ValueError, ZeroDivisionError):
                        pass

            proc.wait()
            t.join(timeout=2)
            ffmpeg_returncode = proc.returncode
            ffmpeg_stderr = ''.join(stderr_buf)
        else:
            result = subprocess.run(
                [ffmpeg_bin, '-y', '-i', temp_path, '-vn', '-acodec', codec,
                 '-b:a', f'{quality}k', final_path],
                capture_output=True, text=True,
            )
            ffmpeg_returncode = result.returncode
            ffmpeg_stderr = result.stderr

        try:
            os.remove(temp_path)
        except Exception:
            pass

        if ffmpeg_returncode != 0 or not os.path.exists(final_path):
            return False, f"ffmpeg conversion failed: {ffmpeg_stderr[-200:]}", None

        if on_progress:
            on_progress(95)

        youtube_thumbnail = yt.thumbnail_url
        analyzed_metadata = _estimate_audio_metadata(final_path)

        if track_info:
            if not track_info.get('album_art_url') and youtube_thumbnail:
                track_info['album_art_url'] = youtube_thumbnail
            for key, value in analyzed_metadata.items():
                track_info.setdefault(key, value)
            add_metadata(final_path, track_info)
        else:
            add_metadata(final_path, {
                'name': yt.title,
                'artist': yt.author,
                'album_art_url': youtube_thumbnail,
                **analyzed_metadata,
            })

        if on_progress:
            on_progress(100)

        return True, "OK", final_path

    except Exception as e:
        error_msg = str(e)
        if "regex_search" in error_msg:
            return False, "Video no disponible", None
        elif "403" in error_msg:
            return False, "Restringido", None
        else:
            return False, error_msg[:30], None


def _fetch_cover_as_jpeg(url: Optional[str]) -> Optional[bytes]:
    """Download cover art and normalize to JPEG. Windows Explorer requires JPEG for thumbnails."""
    if not url:
        return None
    try:
        with without_env_proxies():
            response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return None
        data = response.content
        content_type = response.headers.get('content-type', '').lower()
        # Convert anything that isn't JPEG to JPEG via Pillow
        if 'jpeg' not in content_type and 'jpg' not in content_type:
            try:
                import io
                from PIL import Image
                img = Image.open(io.BytesIO(data))
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                buf = io.BytesIO()
                img.save(buf, format='JPEG', quality=90)
                data = buf.getvalue()
            except Exception:
                pass  # Fall back to raw bytes; at least try to embed
        return data
    except Exception as e:
        print(f"Could not fetch cover art: {e}")
        return None


def _tag_mp3(filepath: str, track_info: dict, cover_data: Optional[bytes]) -> None:
    """Write ID3v2.3 tags to MP3. Windows Explorer thumbnail requires ID3v2.3, not v2.4."""
    from mutagen.mp3 import MP3
    from mutagen.id3 import (
        ID3, TIT2, TPE1, TALB, TDRC, TRCK, APIC, COMM, TBPM, TKEY, USLT,
        ID3NoHeaderError,
    )

    try:
        audio = MP3(filepath, ID3=ID3)
    except ID3NoHeaderError:
        audio = MP3(filepath)
        audio.add_tags()

    for tag in ['TIT2', 'TPE1', 'TALB', 'TDRC', 'TRCK', 'APIC', 'COMM', 'TBPM', 'TKEY', 'USLT']:
        try:
            audio.tags.delall(tag)
        except Exception:
            pass

    if track_info.get('name'):
        audio.tags.add(TIT2(encoding=3, text=track_info['name']))
    if track_info.get('all_artists') or track_info.get('artist'):
        audio.tags.add(TPE1(encoding=3, text=track_info.get('all_artists') or track_info['artist']))
    if track_info.get('album'):
        audio.tags.add(TALB(encoding=3, text=track_info['album']))
    if track_info.get('year'):
        audio.tags.add(TDRC(encoding=3, text=str(track_info['year'])))
    if track_info.get('track_number'):
        audio.tags.add(TRCK(encoding=3, text=str(track_info['track_number'])))
    if track_info.get('spotify_url'):
        audio.tags.add(COMM(encoding=3, lang='eng', desc='spotify', text=track_info['spotify_url']))
    if track_info.get('bpm'):
        audio.tags.add(TBPM(encoding=3, text=str(track_info['bpm'])))
    if track_info.get('key'):
        audio.tags.add(TKEY(encoding=3, text=str(track_info['key'])))
    if track_info.get('lyrics'):
        audio.tags.add(USLT(encoding=3, lang='eng', desc='lyrics', text=str(track_info['lyrics'])))
    if cover_data:
        audio.tags.add(APIC(encoding=3, mime='image/jpeg', type=3, desc='Cover', data=cover_data))

    audio.save(v2_version=3)


def _tag_m4a(filepath: str, track_info: dict, cover_data: Optional[bytes]) -> None:
    """Write metadata to M4A/MP4 container using the covr atom."""
    from mutagen.mp4 import MP4, MP4Cover

    audio = MP4(filepath)
    if audio.tags is None:
        audio.add_tags()

    if track_info.get('name'):
        audio.tags['\xa9nam'] = [track_info['name']]
    if track_info.get('all_artists') or track_info.get('artist'):
        audio.tags['\xa9ART'] = [track_info.get('all_artists') or track_info['artist']]
    if track_info.get('album'):
        audio.tags['\xa9alb'] = [track_info['album']]
    if track_info.get('year'):
        audio.tags['\xa9day'] = [str(track_info['year'])]
    if track_info.get('track_number'):
        audio.tags['trkn'] = [(int(track_info['track_number']), 0)]
    if track_info.get('bpm'):
        audio.tags['tmpo'] = [int(track_info['bpm'])]
    if track_info.get('key'):
        audio.tags['----:com.apple.iTunes:initialkey'] = [str(track_info['key']).encode('utf-8')]
    if track_info.get('lyrics'):
        audio.tags['\xa9lyr'] = [str(track_info['lyrics'])]
    if cover_data:
        audio.tags['covr'] = [MP4Cover(cover_data, imageformat=MP4Cover.FORMAT_JPEG)]

    audio.save()


def _tag_opus(filepath: str, track_info: dict, cover_data: Optional[bytes]) -> None:
    """Write Vorbis comments + METADATA_BLOCK_PICTURE to OGG/OPUS file."""
    import base64
    import struct
    from mutagen.oggopus import OggOpus

    audio = OggOpus(filepath)

    if track_info.get('name'):
        audio['title'] = [track_info['name']]
    if track_info.get('all_artists') or track_info.get('artist'):
        audio['artist'] = [track_info.get('all_artists') or track_info['artist']]
    if track_info.get('album'):
        audio['album'] = [track_info['album']]
    if track_info.get('year'):
        audio['date'] = [str(track_info['year'])]
    if track_info.get('track_number'):
        audio['tracknumber'] = [str(track_info['track_number'])]
    if track_info.get('bpm'):
        audio['bpm'] = [str(track_info['bpm'])]
    if track_info.get('key'):
        audio['initialkey'] = [str(track_info['key'])]
    if track_info.get('lyrics'):
        audio['lyrics'] = [str(track_info['lyrics'])]
    if cover_data:
        mime = b'image/jpeg'
        desc = b''
        # METADATA_BLOCK_PICTURE binary structure (Vorbis comments spec)
        block = (
            struct.pack('>I', 3) +                      # picture type: Cover Front
            struct.pack('>I', len(mime)) + mime +
            struct.pack('>I', len(desc)) + desc +
            struct.pack('>IIII', 0, 0, 0, 0) +          # width/height/depth/colors (0=unknown)
            struct.pack('>I', len(cover_data)) + cover_data
        )
        audio['metadata_block_picture'] = [base64.b64encode(block).decode('ascii')]

    audio.save()


def add_metadata(filepath: str, track_info: dict) -> bool:
    """
    Embed metadata + cover art into the audio file.

    Cover art is always normalized to JPEG before embedding — Windows Explorer
    shell thumbnails require JPEG regardless of the source format.
    ID3 is saved as v2.3 (not v2.4) for the same reason.
    """
    try:
        cover_data = _fetch_cover_as_jpeg(track_info.get('album_art_url'))
        ext = Path(filepath).suffix.lower()

        if ext == '.mp3':
            _tag_mp3(filepath, track_info, cover_data)
        elif ext in ('.m4a', '.mp4'):
            _tag_m4a(filepath, track_info, cover_data)
        elif ext in ('.opus', '.ogg'):
            _tag_opus(filepath, track_info, cover_data)

        return True
    except Exception as e:
        print(f"Error adding metadata to {filepath}: {e}")
        return False
