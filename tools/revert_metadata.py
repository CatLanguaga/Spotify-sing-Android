"""
revert_metadata.py
------------------
Revierte los metadatos de las 50 canciones procesadas por enrich_metadata.py.
Limpia los tags incorrectos (título, artista, álbum, año, track, cover art)
y restaura solo el título basado en el nombre de archivo limpio.
"""

import sys, subprocess, re
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

# ── Mutagen ───────────────────────────────────────────────────────────────────
from mutagen.mp3 import MP3
from mutagen.id3 import (ID3, TIT2, TPE1, TALB, ID3NoHeaderError, APIC)
from mutagen.mp4 import MP4
from mutagen.flac import FLAC

PHONE_DIR  = "/storage/emulated/0/snaptube/download/Snaptube Audio"
TEMP_DIR   = Path("C:/Users/ardie/.openclaw/workspace/temp_meta")
SUPPORTED  = {'.mp3', '.m4a', '.flac'}
TEMP_DIR.mkdir(exist_ok=True)

# Las 50 canciones que procesamos (del reporte anterior)
FILES_TO_REVERT = [
    "4 Non Blondes - Spaceman (Official Music Video)(MP3_320K).mp3",
    "Alhan - Un cuerdo en el manicomio(MP3_320K).mp3",
    "Congratulations_ You Survived Your Suicide(MP3_320K).mp3",
    "Cuarteto de Nos - Breve descripcion de mi persona(M4A_128K).m4a",
    "El Jose -  Un pirata quiero ser (con Mundo Chillón)(MP3_320K).mp3",
    "El Putón del Barrio(MP3_128K).mp3",
    "Estopa - Vacaciones (Videoclip)(MP3_320K).mp3",
    "Girls(MP3_320K).mp3",
    "It_s Not Like I Like You__ – Cover Español(MP3_320K).mp3",
    "La Cantata Del Diablo - Mägo De Oz  Letra(MP3_320K).mp3",
    "La vereda de la puerta de atrás(MP3_320K).mp3",
    "Manu Chao_ me gustas tu - letra(MP3_320K).mp3",
    "Oliver Tree - Miracle Man [Lyric Video](MP3_320K).mp3",
    "Que los Cumpla Feliz.mp3",
    "The 13th tailor「Gospelion in a classic love」 -MUSIC VIDEO-(MP3_320K).mp3",
    "Arco - Lo difícil (Videoclip Oficial)(MP3_320K).mp3",
    "Bacilos - Mi Primer Millon (Official Music Video)(MP3_320K).mp3",
    "Bon Jovi - Bed Of Roses (Official Music Video)(MP3_320K).mp3",
    "Caballo Dorado -  El Diablo Bajo a Georgia (Video Oficial)(MP3_320K).mp3",
    "Cage The Elephant_ Beck - Night Running (Official Audio)(MP3_320K).mp3",
    "Calle 13 - La Vuelta Al Mundo(MP3_320K).mp3",
    "DEAD POSEY - Don_t Stop The Devil(MP3_320K).mp3",
    "EL MUNDO SIEMPRE ESTUVO DIVIDIDO EN DOS (Vid Oficial) - Alan Sutton y las criaturitas de la ansiedad(MP3_320K).mp3",
    "El Che y los Rolling Stones(MP3_320K).mp3",
    "El Cuarteto de Nos - Tiburones en el Bosque (Official Lyric Video)(M4A_128K).m4a",
    "El Diablo Cuenta Su Historia - Green A.m4a",
    "El Ignorante(MP3_320K).mp3",
    "Feed the Machine(MP3_320K).mp3",
    "Frankenstein Posmo(MP3_320K).mp3",
    "Green A - Si pudiera volver a soñar(MP3_320K).mp3",
    "Hay Que Comer(MP3_320K).mp3",
    "Juan Gabriel - Have You Ever Seen The Rain_ (Gracias al Sol)(MP3_320K).mp3",
    "Katy Perry - Birthday (Traducida al español)(MP3_320K).mp3",
    "LOS DE MARRAS _A tu vera_ - Videoclip oficial(MP3_320K).mp3",
    "LOS DE MARRAS _Poeta_ (Audiosingle)(MP3_320K).mp3",
    "La Oreja de Van Gogh - Como Un Par de Girasoles (Audio)(MP3_320K).mp3",
    "La Oreja de Van Gogh - Perdida (Vídeo Oficial)(MP3_320K).mp3",
    "La Vela Puerca - El Profeta(MP3_320K).mp3",
    "La Vela Puerca - Mi Semilla(MP3_320K).mp3",
    "Luck Life - Namae wo yobu yo lyrics_ Bungou Stray Dogs S1 ED 1(MP3_320K).mp3",
    "Mancha de Rolando - Donde vamos (AUDIO)(MP3_320K).mp3",
    "Milky Chance - Stolen Dance (Official Video)(MP3_320K).mp3",
    "Mägo de Oz - Diabulus In Musica(MP3_320K).mp3",
    "No Somos Latinos(MP3_320K).mp3",
    "No Te Va Gustar - Al Vacío (Video Oficial)(MP3_320K).mp3",
    "Palomo(MP3_320K).mp3",
    "Payaso(MP3_320K).mp3",
    "Persona 4 - Heartbeat_ Heartbreak(MP3_320K).mp3",
    "Quiero una gotica Qlona(MP3_320K).mp3",
    "Rayden - La mujer cactus y el hombre globo (Videoclip Oficial)(MP3_320K).mp3",
]

# ── Limpieza de nombre de archivo para título base ────────────────────────────
JUNK_RE = re.compile(
    r'\s*[\(\[\{]?('
    r'MP3_\d+K|M4A_\d+K|FLAC_\d+|'
    r'Official\s*(Music\s*)?Video|Official\s*Audio|Official\s*Lyric\s*Video|'
    r'Videoclip\s*Oficial?|Video\s*Oficial?|Lyric\s*Video|Audio|'
    r'Letra|Lyrics|letra|lyrics|'
    r'Full\s*Version|HD|HQ|4K|'
    r'Vid\s*Oficial?'
    r')[\)\]\}]?',
    re.IGNORECASE
)

def clean_title(stem):
    t = JUNK_RE.sub('', stem).strip()
    t = re.sub(r'[\s_]+$', '', t)
    t = re.sub(r'\s{2,}', ' ', t)
    return t.strip()

# ── ADB helpers ───────────────────────────────────────────────────────────────
def pull(phone_path, local_path):
    cmd = f'adb pull "{PHONE_DIR}/{phone_path}" "{local_path}"'
    subprocess.run(cmd, shell=True, capture_output=True)
    return Path(local_path).exists() and Path(local_path).stat().st_size > 0

def push(local_path, phone_path):
    cmd = f'adb push "{local_path}" "{PHONE_DIR}/{phone_path}"'
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    out = (r.stdout or '') + (r.stderr or '')
    return '1 file' in out or r.returncode == 0

# ── Strip tags y restaurar título limpio ──────────────────────────────────────
def revert_file(filepath):
    ext  = filepath.suffix.lower()
    stem = filepath.stem
    title = clean_title(stem)

    try:
        if ext == '.mp3':
            try:
                tags = ID3(filepath)
            except ID3NoHeaderError:
                tags = ID3()
            # Borrar todo lo que pusimos
            for key in ['TPE1', 'TALB', 'TDRC', 'TRCK', 'TCON', 'APIC']:
                tags.delall(key)
            # Restaurar título limpio
            tags['TIT2'] = TIT2(encoding=3, text=title)
            tags.save(filepath, v2_version=3)
            return True

        elif ext == '.m4a':
            audio = MP4(filepath)
            tags  = audio.tags or audio.add_tags() or audio.tags
            for key in ['\xa9ART', '\xa9alb', '\xa9day', 'trkn', 'covr', '\xa9gen']:
                tags.pop(key, None)
            tags['\xa9nam'] = [title]
            audio.save()
            return True

        elif ext == '.flac':
            audio = FLAC(filepath)
            for key in ['artist', 'album', 'date', 'tracknumber', 'genre']:
                audio.pop(key, None)
            audio.clear_pictures()
            audio['title'] = title
            audio.save()
            return True

    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  ↩️  Revert Metadata — restaurando 50 canciones")
    print("=" * 60)

    ok, fail = [], []

    for i, fname in enumerate(FILES_TO_REVERT, 1):
        print(f"\n[{i:02d}/{len(FILES_TO_REVERT)}] {fname}")
        local = TEMP_DIR / fname

        print("  ⬇️  Pull...")
        if not pull(fname, local):
            print("  ❌ FAIL_PULL")
            fail.append(fname)
            continue

        print("  🧹 Limpiando tags...")
        if not revert_file(local):
            fail.append(fname)
            local.unlink(missing_ok=True)
            continue

        print("  ⬆️  Push...")
        if push(local, fname):
            print("  ✅ Revertido")
            ok.append(fname)
        else:
            print("  ❌ FAIL_PUSH")
            fail.append(fname)

        local.unlink(missing_ok=True)

    print(f"\n{'='*60}")
    print(f"✅ Revertidos: {len(ok)}")
    print(f"❌ Fallidos  : {len(fail)}")
    if fail:
        for f in fail:
            print(f"  • {f}")
    print("=" * 60)

if __name__ == '__main__':
    main()
