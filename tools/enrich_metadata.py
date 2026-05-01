"""
enrich_metadata.py  v2
-----------------------
Lee metadatos de las canciones del teléfono, extrae artista/título del nombre
de archivo de forma inteligente, busca en Spotify, valida el match con fuzzy
matching, y solo escribe si el resultado es confiable.

Reporte detallado en: metadata_report.txt
  ✅ MATCH_OK    → coincidencia confirmada, tags escritos
  ⚠️  NOT_FOUND  → no encontrado en Spotify
  ❌ MISMATCH    → Spotify devolvió algo que no corresponde
  ❌ FAIL_*      → error técnico (pull/push/write)
"""

import sys, os, json, subprocess, re, requests
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

# ── Dependencias ──────────────────────────────────────────────────────────────
from mutagen.mp3  import MP3
from mutagen.id3  import ID3, TIT2, TPE1, TALB, TDRC, TRCK, APIC, ID3NoHeaderError
from mutagen.mp4  import MP4, MP4Cover
from mutagen.flac import FLAC, Picture
from mutagen      import MutagenError
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from unidecode import unidecode
from thefuzz import fuzz

# ── Config ────────────────────────────────────────────────────────────────────
CONFIG_PATH = Path.home() / '.spotifytoyoutube' / 'config.json'
PHONE_DIR   = "/storage/emulated/0/snaptube/download/Snaptube Audio"
TEMP_DIR    = Path("C:/Users/ardie/.openclaw/workspace/temp_meta")
REPORT_PATH = Path("C:/Users/ardie/.openclaw/workspace/metadata_report.txt")
BATCH_SIZE  = 100
BATCH_OFFSET = 50   # saltar las primeras N ya procesadas
SUPPORTED   = {'.mp3', '.m4a', '.flac'}

# Umbral mínimo de similitud para aceptar un match (0-100)
ARTIST_THRESHOLD = 60
TITLE_THRESHOLD  = 55

TEMP_DIR.mkdir(exist_ok=True)

# ── Regex de limpieza ─────────────────────────────────────────────────────────

# Basura genérica entre paréntesis/corchetes conocida
JUNK_RE = re.compile(
    r'[\(\[\{]?'
    r'(?:MP3|M4A|FLAC)_\d+K?'
    r'|Official\s*(?:Music\s*)?(?:Lyric\s*)?(?:Audio\s*)?Video'
    r'|Videoclip\s*Oficial?'
    r'|Video\s*Oficial?'
    r'|Vid\s*Oficial?'
    r'|Lyric\s*Video'
    r'|(?:Full\s*)?Audio(?:single)?'
    r'|Audiosingle'
    r'|Letra(?:s)?'
    r'|Lyrics?'
    r'|Full\s*Version'
    r'|(?:4K|HD|HQ)'
    r'|MUSIC\s*VIDEO'
    r'|Traducida?\s*al\s*[Ee]spañol'
    r'|Cover\s*[Ee]spañol'
    r'|Cover\s*IA\s*\w+'
    r'|Cover'
    r'|Fandub\s*Latino'
    r'|(?:Digital\s*)?Remaster(?:ed)?(?:\s*\d{4})?'
    r'|Sub(?:\.|\.?\s*[Ee]spañol|\s*[Ee]spañol)?'
    r'|Romaji'
    r'[\)\]\}]?',
    re.IGNORECASE
)

# Créditos de producción: [Prod. X] (Prod. X)
PROD_RE   = re.compile(r'[\[\(][Pp]rod\.?[^\]\)]*[\]\)]')

# Features/colaboraciones al final: ft. X  feat. X, Y
FEAT_RE   = re.compile(r'\s+(?:ft|feat)\.?\s+.+$', re.IGNORECASE)

# Contexto entre corchetes/paréntesis con palabras clave no musicales
CTX_RE    = re.compile(
    r'[\[\(][^\[\]()]*'
    r'(?:JJBA|Leitmotif|Musical|Reprise|Nightcore|OST|Episode|Ep\.|'
    r'Fandub|Romaji|Español|español|MV\b)'
    r'[^\[\]()]*[\]\)]',
    re.IGNORECASE
)

# Número al inicio: "3) ", "02. ", "1_ "
LEADING_NUM_RE = re.compile(r'^\d+[\)\.\-_\s]+')

# Separador artista - título
SEP_RE = re.compile(r'\s+[-–—]\s+')


def _base_clean(s):
    """Limpieza básica: JUNK_RE + normalizar espacios."""
    s = JUNK_RE.sub(' ', s)
    s = re.sub(r'[\s_]{2,}', ' ', s)
    return s.strip(' _-–—()')


def _deep_clean(s):
    """Limpieza agresiva: además quita prod credits, feat, contexto, números."""
    s = PROD_RE.sub(' ', s)
    s = CTX_RE.sub(' ', s)
    s = FEAT_RE.sub('', s)
    s = LEADING_NUM_RE.sub('', s)
    s = _base_clean(s)
    return s


def parse_filename(stem):
    """
    Extrae (artist, title) del nombre de archivo (limpieza básica).
    Devuelve ('', título) si no hay separador.
    """
    parts = SEP_RE.split(stem, maxsplit=1)
    if len(parts) == 2:
        return _base_clean(parts[0]), _base_clean(parts[1])
    return '', _base_clean(stem)


def read_existing_tags(filepath):
    """Lee tags actuales del archivo para usar como fallback."""
    ext  = filepath.suffix.lower()
    meta = {'title': '', 'artist': ''}
    try:
        if ext == '.mp3':
            try: tags = ID3(filepath)
            except: tags = {}
            meta['title']  = str(tags.get('TIT2', ''))
            meta['artist'] = str(tags.get('TPE1', ''))
        elif ext == '.m4a':
            tags = MP4(filepath).tags or {}
            meta['title']  = str(tags.get('\xa9nam', [''])[0])
            meta['artist'] = str(tags.get('\xa9ART', [''])[0])
        elif ext == '.flac':
            tags = FLAC(filepath)
            meta['title']  = (tags.get('title')  or [''])[0]
            meta['artist'] = (tags.get('artist') or [''])[0]
    except: pass
    return meta


# ── Spotify ───────────────────────────────────────────────────────────────────
def load_spotify():
    cfg  = json.loads(CONFIG_PATH.read_text())
    auth = SpotifyClientCredentials(
        client_id=cfg['spotify_client_id'],
        client_secret=cfg['spotify_client_secret']
    )
    return spotipy.Spotify(auth_manager=auth)


def _spotify_search_raw(sp, q, limit=5):
    """Ejecuta una búsqueda cruda y devuelve lista de dicts."""
    try:
        res   = sp.search(q=q, type='track', limit=limit)
        return res.get('tracks', {}).get('items', [])
    except Exception as e:
        print(f"     ⚠️  Spotify error: {e}")
        return []


def _has_cjk(s):
    return bool(re.search(r'[\u3040-\u9fff\uac00-\ud7af]', s))


def _build_strategies(artist, title):
    """
    Genera estrategias de búsqueda ordenadas de más a menos específicas.
    - Si tenemos artista Y título claros, las estrategias sueltas NO se usan.
    - title_only / artist_only solo se habilitan cuando falta uno de los dos
      componentes O cuando hay CJK que dificulta el parse.
    """
    da  = _deep_clean(artist)
    dt  = _deep_clean(title)
    cjk = _has_cjk(title + artist)

    # ¿Tenemos ambos componentes identificables?
    both_clear = bool(da and dt and not cjk)

    strats = [
        # Siempre intentamos estas (artista + título en distintas combinaciones)
        ('original',          artist, title,  55),
        ('deep_clean',        da,     dt,     55),
        ('inverted',          title,  artist, 60),
        ('inverted+clean',    dt,     da,     60),
        ('no_feat',           da,     FEAT_RE.sub('', dt).strip(), 60),
        ('strip_num_inv',
            _deep_clean(LEADING_NUM_RE.sub('', title)),
            _deep_clean(LEADING_NUM_RE.sub('', artist)), 65),
    ]

    if both_clear:
        # Con artista+título claros solo permitimos primera palabra del artista
        # pero con umbral alto — no estrategias de un solo componente
        strats.append(('first_word_artist', da.split()[0], dt, 78))
    else:
        # Sin claridad (falta artista, o hay CJK) → permitimos estrategias sueltas
        strats.append(('title_only',        '', dt, 65 if cjk else 72))
        strats.append(('artist_only',       '', da, 70 if cjk else 80))
        strats.append(('first_word_artist', da.split()[0] if da else '', dt, 70))

    seen, unique = set(), []
    for s in strats:
        key = (s[1].lower().strip(), s[2].lower().strip())
        if key not in seen and (s[1] or s[2]):
            seen.add(key)
            unique.append(s)
    return unique


def search_spotify(sp, artist, title):
    """
    Busca en Spotify con cascada de estrategias.
    Cada estrategia tiene su propio umbral mínimo de aceptación.
    Devuelve (dict, score, estrategia) o (None, 0, None).
    """
    strategies = _build_strategies(artist, title)
    best_result, best_score, best_strat = None, 0, None

    for strat_name, sa, st, min_score in strategies:
        if not sa and not st:
            continue

        queries = []
        if sa and st:
            queries.append(f'track:"{st}" artist:"{sa}"')
            queries.append(f'{sa} {st}')
        elif st:
            queries.append(f'track:"{st}"')
            queries.append(st)
        else:
            queries.append(sa)

        strat_best, strat_score = None, 0
        for q in queries:
            for t in _spotify_search_raw(sp, q):
                r     = _to_dict(t)
                score = match_score(sa, st, r['artist'], r['title'])
                if score > strat_score:
                    strat_score, strat_best = score, r
            if strat_score >= 92:
                break

        if strat_best and strat_score >= min_score and strat_score > best_score:
            best_score, best_result, best_strat = strat_score, strat_best, strat_name

        if best_score >= 92:
            break

    return best_result, best_score, best_strat


def _to_dict(t):
    album   = t.get('album', {})
    imgs    = album.get('images', [])
    art_url = imgs[0]['url'] if imgs else None
    return {
        'title':     t['name'],
        'artist':    ', '.join(a['name'] for a in t['artists']),
        'album':     album.get('name', ''),
        'year':      (album.get('release_date', '') or '')[:4],
        'track_num': t.get('track_number', 0),
        'album_art': art_url,
    }


def match_score(search_artist, search_title, found_artist, found_title):
    """
    Calcula un score compuesto (0-100) entre lo buscado y lo encontrado.
    Usa unidecode para ignorar acentos/kana.
    """
    def n(s): return unidecode(s.lower().strip())

    sa, st = n(search_artist), n(search_title)
    fa, ft = n(found_artist),  n(found_title)

    title_score  = fuzz.token_set_ratio(st, ft) if st else 50
    artist_score = fuzz.token_set_ratio(sa, fa) if sa else 50

    # Si no tenemos artista para buscar, damos más peso al título
    if not sa:
        return title_score
    return int(title_score * 0.6 + artist_score * 0.4)


# ── ADB helpers ───────────────────────────────────────────────────────────────
def adb(args):
    return subprocess.run(['adb'] + args, capture_output=True, text=True,
                          encoding='utf-8', errors='replace')


def pull(phone_path, local_path):
    cmd = f'adb pull "{PHONE_DIR}/{phone_path}" "{local_path}"'
    subprocess.run(cmd, shell=True, capture_output=True)
    return Path(local_path).exists() and Path(local_path).stat().st_size > 0


def push(local_path, phone_path):
    cmd = f'adb push "{local_path}" "{PHONE_DIR}/{phone_path}"'
    r   = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                         encoding='utf-8', errors='replace')
    out = (r.stdout or '') + (r.stderr or '')
    return '1 file' in out or r.returncode == 0


# ── Obtener lista ordenada de archivos ────────────────────────────────────────
DATE_RE = re.compile(r'(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})\s+(.*)')


def get_phone_files(limit=50):
    print("📱 Obteniendo archivos del teléfono...")
    r = adb(['shell', f'ls -la "{PHONE_DIR}"'])
    lines = r.stdout.strip().split('\n') + r.stderr.strip().split('\n')

    dated = []
    for line in lines:
        m = DATE_RE.search(line)
        if not m: continue
        date_p, time_p, fname = m.group(1), m.group(2), m.group(3).strip()
        if Path(fname).suffix.lower() not in SUPPORTED: continue
        try:
            dt = datetime.strptime(f"{date_p} {time_p}", "%Y-%m-%d %H:%M")
        except:
            dt = datetime.min
        dated.append((dt, fname))

    dated.sort(key=lambda x: x[0])
    print(f"   {len(dated)} archivos soportados → offset={BATCH_OFFSET}, tomando {limit} archivos")
    return [f for _, f in dated[BATCH_OFFSET:BATCH_OFFSET + limit]]


# ── Escritura de tags ─────────────────────────────────────────────────────────
def download_art(url):
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200: return r.content
    except: pass
    return None


def write_tags(filepath, info, art_data):
    ext = filepath.suffix.lower()
    try:
        if ext == '.mp3':
            try: tags = ID3(filepath)
            except ID3NoHeaderError: tags = ID3()
            tags['TIT2'] = TIT2(encoding=3, text=info['title'])
            tags['TPE1'] = TPE1(encoding=3, text=info['artist'])
            tags['TALB'] = TALB(encoding=3, text=info['album'])
            if info.get('year'):  tags['TDRC'] = TDRC(encoding=3, text=info['year'])
            if info.get('track_num'): tags['TRCK'] = TRCK(encoding=3, text=str(info['track_num']))
            if art_data:
                tags['APIC'] = APIC(encoding=3, mime='image/jpeg',
                                    type=3, desc='Cover', data=art_data)
            tags.save(filepath, v2_version=3)

        elif ext == '.m4a':
            audio = MP4(filepath)
            tags  = audio.tags or audio.add_tags() or audio.tags
            tags['\xa9nam'] = [info['title']]
            tags['\xa9ART'] = [info['artist']]
            tags['\xa9alb'] = [info['album']]
            if info.get('year'):      tags['\xa9day'] = [info['year']]
            if info.get('track_num'): tags['trkn'] = [(int(info['track_num']), 0)]
            if art_data:
                tags['covr'] = [MP4Cover(art_data, imageformat=MP4Cover.FORMAT_JPEG)]
            audio.save()

        elif ext == '.flac':
            audio = FLAC(filepath)
            audio['title']  = info['title']
            audio['artist'] = info['artist']
            audio['album']  = info['album']
            if info.get('year'): audio['date'] = info['year']
            if art_data:
                pic = Picture(); pic.type = 3; pic.mime = 'image/jpeg'; pic.data = art_data
                audio.clear_pictures(); audio.add_picture(pic)
            audio.save()

        return True
    except Exception as e:
        print(f"     ❌ Error tags: {e}")
        return False


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 62)
    print("  🎵 Enrich Metadata v2 — Spotify Edition")
    print("=" * 62)

    # ADB check
    r = adb(['devices'])
    if '\tdevice' not in r.stdout:
        print("❌ Ningún dispositivo ADB conectado."); sys.exit(1)
    dev = [l.split()[0] for l in r.stdout.split('\n') if '\tdevice' in l][0]
    print(f"✅ Dispositivo: {dev}")

    # Spotify
    print("🎧 Conectando Spotify...")
    sp = load_spotify()
    print("✅ Spotify OK")

    # Archivos
    files = get_phone_files(BATCH_SIZE)
    if not files: print("❌ Sin archivos"); sys.exit(1)

    results = []

    for i, fname in enumerate(files, 1):
        print(f"\n[{i:02d}/{len(files)}] {fname}")
        local = TEMP_DIR / fname

        # Pull
        print("  ⬇️  Pull...")
        if not pull(fname, local):
            print("  ❌ FAIL_PULL")
            results.append({'file': fname, 'status': 'FAIL_PULL'})
            continue

        # Parsear nombre de archivo
        stem   = Path(fname).stem
        fa, ft = parse_filename(stem)       # artista y título del filename

        # Leer tags existentes como alternativa
        existing = read_existing_tags(local)
        # Usar tags si son más limpios que el filename
        tag_artist = existing.get('artist', '').strip()
        tag_title  = existing.get('title',  '').strip()

        search_artist = fa or tag_artist
        search_title  = ft or tag_title or stem

        print(f"  🔍 Buscar → artista: «{search_artist}» | título: «{search_title}»")

        # Buscar Spotify (con cascada de fallbacks)
        info, score, strat = search_spotify(sp, search_artist, search_title)

        if not info:
            print(f"  ⚠️  No encontrado en Spotify")
            results.append({'file': fname, 'status': 'NOT_FOUND',
                            'searched': {'artist': search_artist, 'title': search_title}})
            local.unlink(missing_ok=True)
            continue

        print(f"  🎵 [{strat}] score={score} → «{info['title']}» | {info['artist']} | {info['album']} ({info['year']})")

        # Validar match — usamos umbral sobre el score compuesto
        if score < TITLE_THRESHOLD:
            print(f"  ❌ MISMATCH — score={score} < {TITLE_THRESHOLD}")
            results.append({'file': fname, 'status': 'MISMATCH', 'score': score,
                            'strat': strat,
                            'searched': {'artist': search_artist, 'title': search_title},
                            'found':    info})
            local.unlink(missing_ok=True)
            continue

        # Cover art
        art = download_art(info['album_art']) if info.get('album_art') else None
        print(f"  🖼️  Cover: {'✅' if art else '❌'}")

        # Escribir tags
        if not write_tags(local, info, art):
            results.append({'file': fname, 'status': 'FAIL_WRITE',
                            'searched': {'artist': search_artist, 'title': search_title},
                            'found': info})
            local.unlink(missing_ok=True)
            continue

        # Push
        print("  ⬆️  Push...")
        if push(local, fname):
            print(f"  ✅ MATCH_OK (score={score}, strat={strat})")
            results.append({'file': fname, 'status': 'MATCH_OK', 'score': score,
                            'strat': strat,
                            'searched': {'artist': search_artist, 'title': search_title},
                            'found': info, 'art': bool(art)})
        else:
            results.append({'file': fname, 'status': 'FAIL_PUSH',
                            'found': info})

        local.unlink(missing_ok=True)

    write_report(results)
    print(f"\n📄 Reporte: {REPORT_PATH}")


# ── Reporte ───────────────────────────────────────────────────────────────────
def write_report(results):
    ok       = [r for r in results if r['status'] == 'MATCH_OK']
    mismatch = [r for r in results if r['status'] == 'MISMATCH']
    notfound = [r for r in results if r['status'] == 'NOT_FOUND']
    errors   = [r for r in results if r['status'] not in ('MATCH_OK', 'MISMATCH', 'NOT_FOUND')]

    lines = [
        "=" * 62,
        "  📊 REPORTE — Enrich Metadata v2",
        f"  Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "=" * 62,
        f"\nTotal procesadas  : {len(results)}",
        f"✅ Actualizadas   : {len(ok)}",
        f"❌ Mismatch       : {len(mismatch)}",
        f"⚠️  No encontradas : {len(notfound)}",
        f"🔧 Errores técn.  : {len(errors)}",
        "",
        "─" * 62,
        "✅ ACTUALIZADAS CORRECTAMENTE",
        "─" * 62,
    ]
    for r in ok:
        f = r['found']
        lines.append(f"  • {r['file']}")
        lines.append(f"      → «{f['title']}» | {f['artist']} | {f['album']} ({f['year']})")
        lines.append(f"      🔎 Estrategia: {r.get('strat','?')} | score={r['score']} | 🖼️ Cover: {'✅' if r.get('art') else '❌'}")

    lines += ["", "─" * 62, "❌ MISMATCH — Spotify devolvió algo distinto (NO modificadas)", "─" * 62]
    for r in mismatch:
        s = r['searched']
        f = r['found']
        lines.append(f"  • {r['file']}")
        lines.append(f"      Buscado : «{s['title']}» | {s['artist']}")
        lines.append(f"      Encontró: «{f['title']}» | {f['artist']} (score={r['score']}, strat={r.get('strat','?')})")

    lines += ["", "─" * 62, "⚠️  NO ENCONTRADAS EN SPOTIFY", "─" * 62]
    for r in notfound:
        s = r.get('searched', {})
        lines.append(f"  • {r['file']}")
        lines.append(f"      Buscado: «{s.get('title','')}» | {s.get('artist','')}")

    if errors:
        lines += ["", "─" * 62, "🔧 ERRORES TÉCNICOS", "─" * 62]
        for r in errors:
            lines.append(f"  • {r['file']} → {r['status']}")

    lines.append("\n" + "=" * 62)
    text = '\n'.join(lines)
    REPORT_PATH.write_text(text, encoding='utf-8')
    print('\n' + text)


if __name__ == '__main__':
    main()
