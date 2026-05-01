"""
dry_run.py
----------
Busca en Spotify los archivos problemáticos y muestra QUÉ cambiaría,
sin tocar ningún archivo del teléfono.
El usuario aprueba antes de aplicar.
"""
import sys, json, re
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from unidecode import unidecode
from thefuzz import fuzz

# ── Config ────────────────────────────────────────────────────────────────────
CONFIG_PATH  = Path.home() / '.spotifytoyoutube' / 'config.json'
REPORT_PATH  = Path("C:/Users/ardie/.openclaw/workspace/dry_run_report.txt")

# Archivos a revisar (los que dieron metadata incorrecta)
TARGET_FILES = [
    # Lote 1 revertidos
    "El Cuarteto de Nos - El Rey y el As (Pseudo Video)(MP3_320K).mp3",
    "-Dame Da Ne- Baka Mitai - Yakuza OST -  Lyrics (Español - Japones)(MP3_320K).mp3",
    "Queen - Don_t Stop Me Now (Lyrics In Spanish _ English _ Letras en Inglés y en Español)(MP3_320K).mp3",
    "MARINA - You [Official Audio](MP3_320K).mp3",
    "Cage The Elephant - Broken Boy (Official Audio)(MP3_320K).mp3",
    "ロクデナシ「知らないままで」_ Rokudenashi - As you don_t know【Official Music Video】(MP3_320K).mp3",
    "LOS DE MARRAS _Perdido_ (Vídeo)(MP3_320K).mp3",
    "Katy Perry - Cry About It Later (The Smile Video Series)(MP3_320K).mp3",
    # Lote 2 revertidos
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
    "Lower your expectations - Bo Burnham.m4a",
    "Sui Generis - Lunes Otra Vez (Official Audio)(MP3_320K).mp3",
    "Tom Petty- Free Fallin_(MP3_320K).mp3",
    "美波「Llorando por lluvia」( Domestic no Kanojo OP   Letra en español) MV(MP3_320K).mp3",
]

# ── Regex ─────────────────────────────────────────────────────────────────────
JUNK_RE = re.compile(
    r'[\(\[\{]?(?:MP3|M4A|FLAC)_\d+K?'
    r'|Official\s*(?:Music\s*)?(?:Lyric\s*)?(?:Audio\s*)?Video'
    r'|Videoclip\s*Oficial?|Video\s*Oficial?|Lyric\s*Video'
    r'|(?:Full\s*)?Audio(?:single)?|Letra(?:s)?|Lyrics?'
    r'|Full\s*Version|(?:4K|HD|HQ)|MUSIC\s*VIDEO'
    r'|Traducida?\s*al\s*[Ee]spañol|Sub(?:\.\s*[Ee]spañol|\s*español)?'
    r'|Romaji|Fandub\s*Latino|Remaster(?:ed)?(?:\s*\d{4})?'
    r'[\)\]\}]?', re.IGNORECASE
)
PROD_RE        = re.compile(r'[\[\(][Pp]rod\.?[^\]\)]*[\]\)]')
CTX_RE         = re.compile(r'[\[\(][^\[\]()]*(?:JJBA|Leitmotif|Musical|Reprise|Nightcore|OST|Fandub|Romaji|Español|español|MV\b)[^\[\]()]*[\]\)]', re.IGNORECASE)
FEAT_RE        = re.compile(r'\s+(?:ft|feat)\.?\s+.+$', re.IGNORECASE)
LEADING_NUM_RE = re.compile(r'^\d+[\)\.\-_\s]+')
SEP_RE         = re.compile(r'\s+[-–—]\s+')

def _has_cjk(s):
    return bool(re.search(r'[\u3040-\u9fff\uac00-\ud7af]', s))

def _base_clean(s):
    s = JUNK_RE.sub(' ', s)
    s = re.sub(r'[\s_]{2,}', ' ', s)
    return s.strip(' _-–—()')

def _deep_clean(s):
    s = PROD_RE.sub(' ', s)
    s = CTX_RE.sub(' ', s)
    s = FEAT_RE.sub('', s)
    s = LEADING_NUM_RE.sub('', s)
    return _base_clean(s)

def parse_filename(stem):
    parts = SEP_RE.split(stem, maxsplit=1)
    if len(parts) == 2:
        return _base_clean(parts[0]), _base_clean(parts[1])
    return '', _base_clean(stem)

def match_score(sa, st, fa, ft):
    def n(s): return unidecode(s.lower().strip())
    sa, st, fa, ft = n(sa), n(st), n(fa), n(ft)
    ts = fuzz.token_set_ratio(st, ft) if st else 50
    as_ = fuzz.token_set_ratio(sa, fa) if sa else 50
    if not sa: return ts
    return int(ts * 0.6 + as_ * 0.4)

def _build_strategies(artist, title):
    da  = _deep_clean(artist)
    dt  = _deep_clean(title)
    cjk = _has_cjk(title + artist)
    both_clear = bool(da and dt and not cjk)

    strats = [
        ('original',       artist, title,  55),
        ('deep_clean',     da,     dt,     55),
        ('inverted',       title,  artist, 60),
        ('inverted+clean', dt,     da,     60),
        ('no_feat',        da,     FEAT_RE.sub('', dt).strip(), 60),
        ('strip_num_inv',
            _deep_clean(LEADING_NUM_RE.sub('', title)),
            _deep_clean(LEADING_NUM_RE.sub('', artist)), 65),
    ]
    if both_clear:
        strats.append(('first_word_artist', da.split()[0], dt, 78))
    else:
        strats.append(('title_only',        '', dt, 65 if cjk else 72))
        strats.append(('artist_only',       '', da, 70 if cjk else 80))
        strats.append(('first_word_artist', da.split()[0] if da else '', dt, 70))

    seen, unique = set(), []
    for s in strats:
        key = (s[1].lower().strip(), s[2].lower().strip())
        if key not in seen and (s[1] or s[2]):
            seen.add(key); unique.append(s)
    return unique

def search_spotify(sp, artist, title):
    strategies = _build_strategies(artist, title)
    best_result, best_score, best_strat = None, 0, None

    for strat_name, sa, st, min_score in strategies:
        if not sa and not st: continue
        queries = []
        if sa and st:
            queries.append(f'track:"{st}" artist:"{sa}"')
            queries.append(f'{sa} {st}')
        elif st:
            queries.append(f'track:"{st}"'); queries.append(st)
        else:
            queries.append(sa)

        strat_best, strat_score = None, 0
        for q in queries:
            try:
                items = sp.search(q=q, type='track', limit=5).get('tracks',{}).get('items',[])
            except: continue
            for t in items:
                album = t.get('album', {})
                imgs  = album.get('images', [])
                r = {
                    'title':  t['name'],
                    'artist': ', '.join(a['name'] for a in t['artists']),
                    'album':  album.get('name',''),
                    'year':   (album.get('release_date','') or '')[:4],
                    'art':    imgs[0]['url'] if imgs else None,
                }
                score = match_score(sa, st, r['artist'], r['title'])
                if score > strat_score:
                    strat_score, strat_best = score, r
            if strat_score >= 92: break

        if strat_best and strat_score >= min_score and strat_score > best_score:
            best_score, best_result, best_strat = strat_score, strat_best, strat_name
        if best_score >= 92: break

    return best_result, best_score, best_strat

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 65)
    print("  🔍 DRY RUN — Vista previa de cambios (sin tocar archivos)")
    print("=" * 65)

    cfg  = json.loads(CONFIG_PATH.read_text())
    auth = SpotifyClientCredentials(client_id=cfg['spotify_client_id'],
                                    client_secret=cfg['spotify_client_secret'])
    sp   = spotipy.Spotify(auth_manager=auth)
    print("✅ Spotify conectado\n")

    previews = []

    for i, fname in enumerate(TARGET_FILES, 1):
        stem             = Path(fname).stem
        artist, title    = parse_filename(stem)
        search_artist    = artist
        search_title     = title or stem

        print(f"[{i:02d}/{len(TARGET_FILES)}] {fname[:70]}")
        print(f"  🔍 Buscar → artista: «{search_artist}» | título: «{search_title}»")

        result, score, strat = search_spotify(sp, search_artist, search_title)

        if not result:
            print(f"  ⚠️  NO ENCONTRADO en Spotify\n")
            previews.append({'file': fname, 'status': 'NOT_FOUND',
                             'search_artist': search_artist, 'search_title': search_title})
        else:
            # Verificar si el resultado tiene sentido
            title_ok  = fuzz.token_set_ratio(
                unidecode(search_title.lower()), unidecode(result['title'].lower())) >= 55
            artist_ok = (not search_artist or
                         fuzz.token_set_ratio(
                             unidecode(search_artist.lower()), unidecode(result['artist'].lower())) >= 55)
            confidence = "✅ CONFIABLE" if (title_ok and artist_ok) else "⚠️  REVISAR"

            print(f"  🎵 [{strat}] score={score} {confidence}")
            print(f"      Título : «{result['title']}»")
            print(f"      Artista: {result['artist']}")
            print(f"      Álbum  : {result['album']} ({result['year']})")
            print(f"      Cover  : {'✅' if result['art'] else '❌'}\n")
            previews.append({'file': fname, 'status': 'PREVIEW', 'score': score,
                             'strat': strat, 'confidence': confidence,
                             'search_artist': search_artist, 'search_title': search_title,
                             'result': result})

    # Escribir reporte
    write_report(previews)
    print(f"\n📄 Reporte guardado: {REPORT_PATH}")
    print("\n⏸️  Revisa el reporte y aprueba los cambios antes de aplicar.")

def write_report(previews):
    ok       = [p for p in previews if p['status']=='PREVIEW' and '✅' in p['confidence']]
    review   = [p for p in previews if p['status']=='PREVIEW' and '⚠️' in p['confidence']]
    notfound = [p for p in previews if p['status']=='NOT_FOUND']

    lines = [
        "=" * 65,
        "  🔍 DRY RUN REPORT — Cambios propuestos",
        f"  (Ningún archivo fue modificado)",
        "=" * 65,
        f"\nTotal archivos   : {len(previews)}",
        f"✅ Confiables    : {len(ok)}",
        f"⚠️  Revisar       : {len(review)}",
        f"❌ No encontrados: {len(notfound)}",
        "",
        "─" * 65,
        "✅ CAMBIOS CONFIABLES (artista + título verificados)",
        "─" * 65,
    ]
    for p in ok:
        r = p['result']
        lines.append(f"\n  📁 {p['file']}")
        lines.append(f"     Buscado  → artista: «{p['search_artist']}» | título: «{p['search_title']}»")
        lines.append(f"     Resultado→ «{r['title']}» | {r['artist']} | {r['album']} ({r['year']})")
        lines.append(f"     Score: {p['score']} | Estrategia: {p['strat']} | Cover: {'✅' if r['art'] else '❌'}")

    lines += ["", "─" * 65, "⚠️  REQUIEREN REVISIÓN MANUAL", "─" * 65]
    for p in review:
        r = p['result']
        lines.append(f"\n  📁 {p['file']}")
        lines.append(f"     Buscado  → artista: «{p['search_artist']}» | título: «{p['search_title']}»")
        lines.append(f"     Resultado→ «{r['title']}» | {r['artist']} | {r['album']} ({r['year']})")
        lines.append(f"     Score: {p['score']} | Estrategia: {p['strat']}")
        lines.append(f"     ⚠️  El artista o título no coincide bien — verificar manualmente")

    lines += ["", "─" * 65, "❌ NO ENCONTRADAS EN SPOTIFY", "─" * 65]
    for p in notfound:
        lines.append(f"\n  📁 {p['file']}")
        lines.append(f"     Buscado → artista: «{p['search_artist']}» | título: «{p['search_title']}»")

    lines.append("\n" + "=" * 65)
    REPORT_PATH.write_text('\n'.join(lines), encoding='utf-8')

if __name__ == '__main__':
    main()
