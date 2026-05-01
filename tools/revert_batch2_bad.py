"""
revert_batch2_bad.py — Revierte los archivos con metadata incorrecta del lote 2.
"""
import sys, subprocess, re
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

from mutagen.id3 import ID3, TIT2, ID3NoHeaderError
from mutagen.mp4 import MP4
from mutagen.flac import FLAC

PHONE_DIR = "/storage/emulated/0/snaptube/download/Snaptube Audio"
TEMP_DIR  = Path("C:/Users/ardie/.openclaw/workspace/temp_meta")
TEMP_DIR.mkdir(exist_ok=True)

JUNK_RE = re.compile(
    r'[\(\[\{]?(?:MP3|M4A|FLAC)_\d+K?'
    r'|Official\s*(?:Music\s*)?(?:Lyric\s*)?(?:Audio\s*)?Video'
    r'|Videoclip\s*Oficial?|Video\s*Oficial?|Lyric\s*Video'
    r'|(?:Full\s*)?Audio(?:single)?|Letra(?:s)?|Lyrics?'
    r'|Full\s*Version|(?:4K|HD|HQ)|MUSIC\s*VIDEO'
    r'|Traducida?\s*al\s*[Ee]spañol|Sub(?:\.\s*[Ee]spañol)?'
    r'[\)\]\}]?', re.IGNORECASE
)

BAD_FILES = [
    "Los Bunkers _ Bailando Solo [video oficial](M4A_128K).m4a",
    "Cuarteto de Nos - Cuando Sea Grande (Video Lyric)(M4A_128K).m4a",
    "Sui Generis - Necesito (Official Audio)(MP3_320K).mp3",
    "Los De Marras - Revolviendo (Surrealismo) [Audio Oficial](MP3_320K).mp3",
    "HAZMETUYAH(MP3_320K).mp3",
    "Enrico Pucci - Made In Heaven (JJBA Musical Leitmotif)(M4A_128K)_1.m4a",
    "Ska-P - Paramilitar (Vidioclip)(MP3_320K).mp3",
    "El sueño de Morfeo - Esta soy yo (video clip)(MP3_320K).mp3",
    "Dividing By Zero_Slim Pickens Does The Right Thing And Rides The Bomb To Hell (Official Video)(M4A_128K)_1.m4a",
    "お気に召すまま - Eve MV(M4A_128K)_1.m4a",
    "the pretty reckless - heaven knows __ sub. español(MP3_320K).mp3",
    "麦吉_Maggie x 盖盖Nyan - Summertime (Arrange ver.)(MP3_320K).mp3",
    "Ska-P - Legalización(MP3_320K).mp3",
    "Riccie Oriach _ Munir Hossn - Viene el Aguacero(MP3_320K).mp3",
    "ドラマツルギー - Eve  MV(MP3_320K).mp3",
    # del lote anterior
    "Lower your expectations - Bo Burnham.m4a",
    "Sui Generis - Lunes Otra Vez (Official Audio)(MP3_320K).mp3",
    "Tom Petty- Free Fallin_(MP3_320K).mp3",
    "美波「Llorando por lluvia」( Domestic no Kanojo OP   Letra en español) MV(MP3_320K).mp3",
    "ロクデナシ「知らないままで」_ Rokudenashi - As you don_t know【Official Music Video】(MP3_320K).mp3",
    "LOS DE MARRAS _Perdido_ (Vídeo)(MP3_320K).mp3",
]

def clean_title(stem):
    t = JUNK_RE.sub(' ', stem)
    t = re.sub(r'[\s_]{2,}', ' ', t).strip(' _-–—()')
    return t

def pull(fname, local):
    cmd = f'adb pull "{PHONE_DIR}/{fname}" "{local}"'
    subprocess.run(cmd, shell=True, capture_output=True)
    return Path(local).exists() and Path(local).stat().st_size > 0

def push(local, fname):
    cmd = f'adb push "{local}" "{PHONE_DIR}/{fname}"'
    r = subprocess.run(cmd, shell=True, capture_output=True,
                       text=True, encoding='utf-8', errors='replace')
    return '1 file' in (r.stdout + r.stderr) or r.returncode == 0

def revert(filepath):
    ext   = filepath.suffix.lower()
    title = clean_title(filepath.stem)
    try:
        if ext == '.mp3':
            try: tags = ID3(filepath)
            except ID3NoHeaderError: tags = ID3()
            for key in ['TPE1','TALB','TDRC','TRCK','APIC','TCON']:
                tags.delall(key)
            tags['TIT2'] = TIT2(encoding=3, text=title)
            tags.save(filepath, v2_version=3)
        elif ext == '.m4a':
            audio = MP4(filepath)
            tags  = audio.tags or audio.add_tags() or audio.tags
            for k in ['\xa9ART','\xa9alb','\xa9day','trkn','covr','\xa9gen']:
                tags.pop(k, None)
            tags['\xa9nam'] = [title]
            audio.save()
        elif ext == '.flac':
            audio = FLAC(filepath)
            for k in ['artist','album','date','tracknumber','genre']:
                audio.pop(k, None)
            audio.clear_pictures()
            audio['title'] = title
            audio.save()
        return True
    except Exception as e:
        print(f"  ❌ {e}"); return False

def main():
    print("="*55)
    print(f"  ↩️  Revirtiendo {len(BAD_FILES)} archivos con metadata incorrecta")
    print("="*55)
    ok, fail, skip = [], [], []

    for i, fname in enumerate(BAD_FILES, 1):
        print(f"\n[{i:02d}/{len(BAD_FILES)}] {fname[:65]}...")
        local = TEMP_DIR / fname

        print("  ⬇️  Pull...")
        if not pull(fname, local):
            print("  ⚠️  FAIL_PULL (archivo puede no existir exactamente así)")
            skip.append(fname)
            continue

        print("  🧹 Limpiando tags...")
        if not revert(local):
            fail.append(fname)
            local.unlink(missing_ok=True)
            continue

        print("  ⬆️  Push...")
        if push(local, fname):
            print("  ✅ OK")
            ok.append(fname)
        else:
            print("  ❌ FAIL_PUSH")
            fail.append(fname)
        local.unlink(missing_ok=True)

    print(f"\n{'='*55}")
    print(f"✅ Revertidos : {len(ok)}")
    print(f"⏭️  Skipped    : {len(skip)}")
    print(f"❌ Fallidos   : {len(fail)}")
    if skip:
        print("\nSkipped (verificar nombres):")
        for f in skip: print(f"  • {f}")

if __name__ == '__main__':
    main()
