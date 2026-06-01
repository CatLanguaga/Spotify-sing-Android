# Web Roadmap — Spotify Downloader Portal

**Objetivo:** Portal web Docker-friendly para descargar música de Spotify directo al dispositivo del usuario. Sin ADB, sin comparación con teléfono.

**Referentes UX:**
- [cobalt.tools](https://cobalt.tools) — input único, proceso inmediato, minimalismo radical
- [metube](https://github.com/alexta69/metube) — queue visual, progreso en tiempo real, auto-download al browser
- [Exportify](https://exportify.net) — login Spotify OAuth, grid de playlists, UX limpia
- [spotDL web](https://github.com/spotDL/spotify-downloader) — mismo core técnico

**Pivot vigente (2026-05-26):** single-page, sin cola persistente. Resultados inline, descarga directa al browser. Referencia visual: `gui/design-demos/demo-singlepage.html`.

---

## 🎯 Estado actual

| Fase | Estado | Notas |
|---|---|---|
| 1 — Eliminar ADB | ✅ Completa | |
| 2 — Backend download-to-browser | ✅ Completa | usa `pytubefix` en lugar de `yt-dlp` |
| 3 — Frontend web-first | ✅ Completa | Cola/Sidebar/multi-select N/A por pivot single-page; paginación diferida a Fase 4 |
| 4 — Paginación 50 tracks | ✅ Completa | slider reemplazado por paginador clásico (prev/next + números); offset/limit por página |
| 5 — UX Polish | ✅ Completa | |
| 6 — Matching YouTube | ✅ Completa | |
| 6.5 — Metadatos completos | ✅ Completa | portada JPEG embebida; ID3v2.3; M4A covr; OPUS METADATA_BLOCK_PICTURE |
| 6.6 — QoL: batch + paginación + idioma | ⏳ En progreso | descarga simultánea con manejo de errores; salto directo de página; filtro de idioma con langdetect |
| 7 — SEO + estructura | ⏳ En progreso | SEO 100, accesibilidad 100 y performance 95 en Lighthouse; LCP/CLS dentro de objetivo |
| 7.5 — Contenido SEO + claridad | ⏳ En progreso | ampliar landing con que es la página, características, tutorial, límites y FAQs útiles |
| 8 — Features adicionales | 📋 Backlog priorizado | |
| 9 — Arquitectura Docker | ⏳ Pendiente | pre-deploy |
| 10 — Deploy | ⏳ Pendiente | depende de Fase 9 |

---

## Fase 1 — Eliminar código ADB / teléfono

- [x] Borrar `gui/backend/routes/adb.py` completo
- [x] En `queue.py`: eliminar `_adb_connected()`, `_push_to_phone()`, `PHONE_MUSIC_DIR`, lógica de push
- [x] En `queue.py`: el download siempre guarda en `DOWNLOAD_DIR` local
- [x] En `models.py`: eliminar campos relacionados a ADB/phone si existen
- [x] Frontend — eliminar `AdbConnectModal.tsx`
- [x] Frontend — eliminar indicador ADB del sidebar
- [x] Frontend — eliminar `CompareView` entera (comparar Spotify vs teléfono no aplica)
- [x] Frontend — eliminar botón "Download to Phone" / label dinámico PC/Android
- [x] Limpiar `main.py` del backend: quitar router ADB

---

## Fase 2 — Backend: download-to-browser

El flujo: el servidor descarga el archivo → el browser lo recibe automáticamente.

- [x] Nuevo endpoint `GET /api/queue/{item_id}/file` — sirve el archivo descargado como `FileResponse` con `Content-Disposition: attachment`
- [x] El frontend hace `window.location.href = /api/queue/{id}/file` tras descarga exitosa → browser descarga el archivo
- [x] Limpieza automática: borrar archivo del servidor X minutos después de servido (evitar llenado de disco)
- [x] Endpoint `POST /api/download/direct` — recibe URL de Spotify o playlist, retorna job_id inmediatamente, procesa en background
- [x] `GET /api/download/{job_id}/status` — polling de estado (o WebSocket ya existente)
- [x] Validar que `yt-dlp` y `ffmpeg` están disponibles en Docker antes de aceptar solicitudes (nota: proyecto usa `pytubefix` en lugar de `yt-dlp`; se valida `pytubefix` + `ffmpeg`)

---

## Fase 3 — Frontend: rediseño web-first

> Implementada 2026-05-27 contra `gui/design-demos/demo-singlepage.html` (single-page pivot). Items de Cola/Sidebar/selección múltiple superseded por pivot — marcados N/A.

### Vista principal — Search / Import

> Inspiración: cobalt.tools. Una sola acción domina la pantalla.

- [x] Hero con input grande: pegar URL de Spotify (track, álbum, o playlist) → `components/HeroSearch.tsx`
- [x] Validación en tiempo real: detectar tipo (track / album / playlist) y mostrarlo con ícono (chip "✓ detectado")
- [x] Botón "Buscar" → llama `GET /api/spotify/resolve?url=` → muestra resultados (scroll a `#results`)
- [x] Estado vacío elegante con instrucciones y ejemplos de URLs válidas (chips track/álbum/playlist)

### Vista de Playlist / Álbum

> Inspiración: Exportify (grid de tracks), metube (selección múltiple). NOTA: pivot a single-page eliminó cola persistente y checkbox-select — cada track descarga directo al browser.

- [x] Header con cover art grande, nombre de playlist, total de tracks, duración total → `components/PlaylistCard.tsx`
- [x] Tabla de tracks: cover (44px), título, artista, duración, idioma badge → `components/TrackRow.tsx`
- [~] ~~Selección múltiple: checkbox por fila + "Seleccionar todos" en header~~ — N/A (pivot single-page, "Descargar todo" reemplaza)
- [~] ~~Barra inferior sticky con "Agregar a cola"~~ — N/A (sin cola; format/quality + "Descargar todo" en header del card)
- [x] Filtro por texto (nombre/artista)
- [x] Filtro por idioma — `PlaylistCard.tsx` filtra por badges de idioma
- [ ] Paginación o scroll infinito — diferido a Fase 4 (range slider con clamp 50)

### Vista de Cola (Queue)

> SUPERSEDED — pivot single-page eliminó cola persistente. Estados de descarga viven inline en `TrackRow` (idle → downloading → done/err) con mini progress bar + auto-download al browser via `/api/queue/{id}/file`.

- [~] ~~Cards compactas con progreso~~ — N/A (inline mini progress bar en TrackRow)
- [x] Estados: `idle → downloading → done ✓ / err ✗` (TrackRow state machine)
- [x] Al llegar a "done": descarga automática vía `window.location.href = /api/queue/{id}/file`
- [x] Botón de retry en estado error (TrackRow muestra "↻ Reintentar")
- [x] "Descargar todo" — batch con stagger 180ms (PlaylistCard `downloadAll`)
- [x] Contador de progreso batch: `N de M descargados` en `.pl-foot`
- [~] ~~Limpiar completados~~ — N/A (sin cola persistente)

### Vista de Configuración

- [x] Campos: Spotify Client ID, Spotify Client Secret (con link a developer.spotify.com) → `views/SettingsView.tsx`
- [x] Formato por defecto (mp3 / m4a / opus) y calidad (128 / 192 / 320 kbps)
- [x] Test de conexión Spotify: botón "Verificar credenciales" (pega a `/api/spotify/status`)
- [x] Sin campos de ADB, sin carpeta de descarga
- [x] Info visual sobre cómo crear una Spotify App — guía paso a paso en `SettingsView.tsx`

### Sidebar / Navegación

> SUPERSEDED — pivot single-page reemplazó sidebar por `components/Topbar.tsx` con nav horizontal.

- [~] ~~Sidebar~~ — N/A. Topbar con: brand → Inicio · ¿Cómo funciona? · FAQ · Configuración
- [x] Sin item "Compare" ni indicadores ADB
- [~] ~~Badge en "Cola"~~ — N/A (sin cola)
- [x] Logo + nombre de la app en topbar

---

## Fase 4 — UX de visualización: paginación por páginas (50 tracks/página)

> Decisión de diseño confirmada (2026-05-26): pivot a single-page, sin cola persistente. Resultados inline, descarga directa. Ver `gui/design-demos/demo-singlepage.html`.
> Rediseño (2026-05-30): range slider reemplazado por paginador clásico — más simple, sin ambigüedad de arrastre.

### Límite de 50 tracks por consulta

- [x] Constante backend `MAX_TRACKS_PER_REQUEST = 50` en `src/config.py` o env var
- [x] `GET /api/spotify/resolve?url=&offset=&limit=` — siempre `limit ≤ 50`
- [x] Backend ignora `limit > 50` y aplica clamp silencioso
- [x] Si `playlist.total > 50`: response incluye `total`, `returned`, `offset` — el frontend renderiza el paginador
- [x] Cache de metadata Spotify por `playlist_id` (TTL 10 min)

### Paginador (frontend) — `TrackPaginator.tsx`

- [x] Componente `<TrackPaginator />` reemplaza `<TrackRangeSlider />` (eliminado)
- [x] Botones `← Anterior` / `Siguiente →` con disabled en extremos
- [x] Números de página: si ≤ 7 páginas muestra todos; si > 7 usa ellipsis (`1 … 4 5 6 … 12`)
- [x] Texto auxiliar: `Página X de Y · tracks A–B de C`
- [x] Spinner inline durante carga de página
- [x] `offset = (page - 1) * 50` — fetch a `/api/spotify/resolve?offset=N&limit=50` al cambiar página
- [x] Tracks anteriores reemplazados en memoria — sin acumulación
- [x] Debounce 200 ms + cancelación de requests in-flight (requestSeq)
- [x] Estado URL: `?page=2` para deep-link / share
- [x] Persistir última página en `localStorage` → `spotify-page:{id}`

### Edge cases

- [x] Playlist ≤ 50: ocultar paginador, mostrar todo
- [x] Track individual / álbum < 50: sin paginador
- [x] Loading skeleton mientras refetch (no parpadeo de tabla)
- [x] Página fuera de rango: clamp automático a `[1, totalPages]`

---

## Fase 5 — UX Polish

### Flujo rápido (single-track)

- [x] Auto-búsqueda al ingresar/pegar una URL válida: tan pronto el input detecte una URL de Spotify completa, ejecutar `GET /api/spotify/resolve?url=` sin exigir click en "Buscar" (debounce corto + evitar re-buscar la misma URL)
- [x] Para URLs de track individual: saltarse playlist view, ir directo a cola con el track pre-cargado
- [x] Modal de confirmación mínimo: formato + calidad + "Descargar ahora"

### Feedback visual

- [x] Toast notifications para: track agregado a cola, descarga lista, error
- [x] Skeleton loaders en playlist view mientras carga
- [x] Animación de progreso real — `download_audio` acepta `on_progress` callback; pytubefix reporta 5-65% por bytes, ffmpeg `-progress pipe:1` reporta 65-95%; SSE endpoint `GET /queue/{id}/progress`; frontend usa `EventSource` + barra indeterminate durante fase de resolución (Spotify+YT, ~3-7s).

### Responsive / Mobile

- [x] La app debe funcionar en móvil (descargar desde el teléfono)
- [x] Topbar colapsa a bottom navigation en mobile
- [x] Cards apiladas, touch-friendly (48px min tap targets)
- [x] Input de URL acepta Share desde Spotify mobile

---

## Fase 6 — Mejorar matching YouTube (reducir errores y descargas erróneas)

### Scoring del match

- [x] Algoritmo de score considera: duración (±3s del Spotify duration), artista normalizado (lowercase, sin features), título normalizado (quitar `(Official Video)`, `[MV]`, `Lyric Video`, etc.), año, canal verificado
- [x] Threshold mínimo: si `score < 65` y `manual_review_enabled=true` → modal de revisión con top 3 alternativas; si `false` → auto-descarga mejor resultado
- [x] Threshold óptimo: si `score ≥ 90` en primera query → early exit sin cascada completa

### Estrategias de búsqueda

- [x] Query primaria: `"Artista" "Título" topic` (canales "Topic" de YouTube son re-uploads oficiales del label, suelen ser exactos)
- [x] Fallback 1: `"Artista" "Título" audio` (excluye videos)
- [x] Fallback 2: `"Artista" "Título" lyrics` (suele ser audio limpio)
- [x] Fallback 3: query simple sin comillas
- [x] Filtrar resultados con duración fuera de ±10s del track Spotify
- [x] Penalizar canales con palabras flag: `cover`, `remix`, `karaoke`, `8d`, `slowed`, `sped up`, `nightcore`, `live` (a menos que el track Spotify ya sea live)

### Manual override

- [x] Botón "🔍 Buscar manualmente" en cada track — solo visible cuando `manual_review_enabled=true` → `ManualSearchModal` con search bar YouTube + lista de candidatos con thumbnail/score
- [x] Sección "Pegar URL de YouTube" en el modal para forzar source específico
- [x] Persistir overrides por `spotify_id` en `localStorage` — próxima descarga del mismo track usa el override directamente sin buscar

### Caché y resiliencia

- [x] Caché in-memory de búsqueda YouTube por `spotify_id` (TTL 1h) — `_YT_CACHE` en `download.py`
- [x] Detección de geo-restricción YouTube: error en `_bg_download` detecta "geo" / "not available" → estado `geo_restricted` vía SSE

### Calidad del audio source

- [x] Preferir streams con bitrate más alto disponible (ya implementado)
- [~] Warning si bitrate del source < bitrate solicitado — diferido (requiere pre-inspección del stream antes de descargar)
- [~] Detectar streams cortos (intros/sketches) — cubierto parcialmente por filtro de duración ±10s

### Metadatos Spotify en archivos descargados

- [x] Escribir tags desde Spotify: título, artistas, álbum, número de track, año/fecha, portada del álbum, `spotify_id` y `spotify_url` como tag COMM
- [~] Imagen/metadata de artista adicional — cover art del álbum ya se escribe; metadata de artista separada no disponible en API básica
- [x] Portada de YouTube como fallback si Spotify no entrega cover art

---

## Fase 6.5 — Metadatos completos: portada visible en explorador de archivos

> Problema: la portada de Spotify se escribe en los tags, pero solo la leen reproductores (VLC, etc.). El Explorador de Windows y Finder no la muestran como miniatura del archivo.

### Causa raíz

El tag `APIC` (ID3v2) debe cumplir condiciones específicas para que el shell lo renderice:

- **MP3**: tag `APIC` con `picture_type=3` (Cover Front), mime `image/jpeg`, imagen embebida como bytes dentro del ID3v2 header. Windows Shell Extension lee esto si el archivo tiene ID3v2.3 o ID3v2.4.
- **M4A/MP4**: átomo `covr` dentro del container MP4 — distinto mecanismo. `mutagen.MP4` usa `MP4Cover`.
- **OPUS/OGG**: `METADATA_BLOCK_PICTURE` en Vorbis comments — base64 encoded.

### Tareas

- [x] Verificar que `mutagen` escribe el tag `APIC` con `picture_type=3` (Cover Front) y `encoding=3` (UTF-8) — no `picture_type=0` (Other), que Windows ignora para thumbnails.
- [x] Para MP3: forzar ID3 versión 2.3 (`v2_version=3`) al guardar — Windows Explorer no soporta ID3v2.4 para thumbnails.
- [x] Para M4A: usar `mutagen.mp4.MP4Cover` con `imageformat=MP4Cover.FORMAT_JPEG` al escribir el átomo `covr`.
- [x] Para OPUS: convertir cover art a `METADATA_BLOCK_PICTURE` base64 en Vorbis comments.
- [x] Descargar portada Spotify en JPEG (no WebP) — el Shell Extension de Windows no decodifica WebP en thumbnails.
- [x] Si la imagen de Spotify viene en formato distinto a JPEG, convertir con `Pillow` antes de embeber.
- [ ] Test manual: archivo descargado → ver thumbnail en Explorador de Windows sin abrir el archivo.
- [ ] Test en Finder (macOS) si aplica al deploy.

### Notas técnicas

- Spotify entrega covers en `https://i.scdn.co/image/...` como JPEG normalmente, pero verificar content-type antes de asumir.
- `mutagen.id3.APIC` acepta `data=bytes` — descargar con `requests.get(cover_url).content` y pasar directo.
- Windows Explorer usa el **Windows Shell Extension para MP3** que está deshabilitado en Windows 11 por defecto si el archivo no tiene el thumbnail cacheado. Forzar refresh con `ie4uinit.exe -show` o simplemente abrir una carpeta nueva.

---

## Fase 6.6 — Calidad de vida: batch download, navegación de páginas, filtro de idioma

> Mejoras de UX pedidas tras uso real. Decisiones: batch = individual (default) + ZIP opcional; idioma = `langdetect` primario + heurística de respaldo.

### Descarga simultánea de las 50 visibles + manejo de errores

> Problema detectado: "Descargar todo" falla. Causas:
> 1. Frontend usa `window.location.href` por track (`TrackRow.tsx:95`) — navegación única; 50 asignaciones rápidas se cancelan, solo baja la última.
> 2. Backend: 50 hilos `_bg_download` hacen read-modify-write sobre `queue.json` sin lock (`queue.py:44-60`) → lost-update → `local_path` se pierde → `/file` devuelve `{"detail":"File not found — download it first."}`.
> 3. Concurrencia ilimitada satura red/CPU.

- [x] Backend: lock `_QUEUE_LOCK` + helper atómico `_patch_item(item_id, **fields)` (load→mutar→save bajo lock) en `queue.py`; `_bg_download` lo usa en vez de `_load()`/`_update_item`
- [x] Backend: `Semaphore(MAX_CONCURRENT_DOWNLOADS=3)` en el spawn de hilos (`download.py`) — encola las 50, corren N a la vez
- [x] Frontend: reemplazar `window.location.href` por helper `triggerBrowserDownload(url)` (anchor `<a download>` + click) → permite múltiples descargas concurrentes. Extraer a `api/download.ts`
- [x] Frontend: orquestación batch en `PlaylistCard` con pool (concurrencia 3-4); al recibir `onStateChange` despacha el siguiente — reemplaza el stagger `trigger + i*180ms`
- [x] Manejo de errores: track en `error` → retry automático hasta 2 veces; batch NO se detiene por un fallo
- [x] Resumen final: toast `N descargadas · M con error` + botón "Reintentar fallidas" (reencola solo las `error`)
- [x] ZIP opcional: endpoint `POST /api/download/batch` (recibe `spotify_ids[]`, fmt, quality) → job_id, descarga + `zipfile`; SSE `…/batch/{job_id}/progress`; `GET …/batch/{job_id}/zip` (`FileResponse` + cleanup); botón "Descargar ZIP" en header del card
- [x] Sanitizar nombres dentro del zip (colisiones / CJK)

### Navegación de páginas — salto directo

> `TrackPaginator.tsx` solo tiene prev/next + números con ellipsis. Saltar a la página 27 exige clickear una por una.

- [x] Input numérico "Ir a página" + botón "Ir" dentro de `.paginator-controls` (`TrackPaginator.tsx`)
- [x] `min=1 max=totalPages`; Enter o click → clamp `[1, totalPages]` → `onPageChange(n)`
- [x] Estilos `.paginator-jump` replicando `.paginator-page` (36px, `1px solid var(--rule)`, radius 8px) en `index.css`
- [x] Reusa flujo existente de fetch/offset/URL `?page=`/localStorage — sin cambios en esa capa

### Filtro de idioma — corregir misclasificación

> Problema: español clasificado como inglés. `_detect_language_smart` (`src/spotify_client.py:113-194`) solo detecta ES por `ñ` o set chico de stopwords; si no matchea → default inglés. Frontend además hace default a `'EN'` (`LangBadge.tsx:18`).

- [x] Backend: mantener detección por script para no-latino (CJK, hiragana/katakana, hangul, cirílico, árabe)
- [x] Backend: para texto latino usar `langdetect.detect_langs(title+artist+album)`; si confianza ≥ umbral (~0.85) y código en {es,en,pt,it,fr} → mapear a nombre
- [x] Backend: fallback heurístico cuando langdetect tiene baja confianza o texto corto — stopwords ampliados es/pt/it/fr con scoring (gana el de más matches), sin default ciego a inglés; empate/cero → "Other"
- [x] Backend: `DetectorFactory.seed = 0` (langdetect no-determinista); añadir `langdetect` a `requirements.txt`
- [x] Frontend: quitar default `'EN'` → `'OTHER'` en `LangBadge.tsx`, `TrackRow.tsx`, `PlaylistCard.tsx`; añadir PT/IT/FR. Mapeo extraído a util compartido `api/langLabel.ts`

---

## Fase 7 — SEO + estructura de página

> Implementación base completada con skills SEO. Lighthouse local actualizado (`logs/lighthouse-phase75-final.json`) en Edge headless: SEO 100, accesibilidad 100, best practices 100, performance 95.

### Meta + structured data

- [x] `<title>`, `<meta description>`, `<meta og:*>`, `<meta twitter:*>` dinámicos por vista — `src/seo.ts`
- [x] `<link rel="canonical">` correcto — HTML inicial + runtime por ruta
- [x] JSON-LD `WebApplication` schema en home — HTML inicial + runtime
- [x] `robots.txt` + `sitemap.xml` (rutas `/`, `/how-it-works`, `/faq`, `/settings`) — `public/`
- [x] `<html lang="es">` + atributo `lang` por sección si hay multi-idioma

### Performance / Core Web Vitals

- [x] Lazy-load de covers (`loading="lazy"`)
- [x] Preconnect a Spotify CDN (`i.scdn.co`)
- [x] Fonts: stack del sistema sin fuente remota para evitar CLS por webfont
- [~] Inline critical CSS, defer no-critical — font CSS diferido; app CSS sigue siendo render-blocking
- [x] LCP < 2.5s, CLS < 0.1, INP < 200ms — Lighthouse: LCP 2.3s, CLS 0, TBT 60ms

### Estructura semántica

- [x] `<header>`, `<main>`, `<section>`, `<footer>` correctos
- [x] Heading hierarchy sin saltos (h1 → h2 → h3)
- [x] `<details>/<summary>` para FAQ (ya implementado en demo)
- [x] ARIA labels en botones de descarga e input principal
- [x] Focus rings visibles, navegación por teclado completa
- [x] Skip-link "Saltar al contenido"

### Accesibilidad WCAG AA mínimo

- [x] Contraste texto ≥ 4.5:1 (verificar acento verde sobre blanco)
- [x] `prefers-reduced-motion` respetado en animaciones
- [x] `aria-live` para estados de descarga (lector de pantalla anuncia "descargado")
- [x] Labels asociados a todos los inputs (`<label for>`)

---

## Fase 7.5 — Contenido SEO + claridad de la página

> Enfoque: enriquecer la landing con contenido útil, explicativo y escaneable para usuarios y buscadores. Usar criterios de SEO content: respuesta directa, cobertura de intención, FAQs citables y lenguaje natural sin keyword stuffing.

### Contenido principal

- [x] Sección "Qué es esta página" con definición clara de Spotify Sing y su flujo real.
- [x] Características principales: links de Spotify, metadata, formatos, playlists grandes, filtros y descarga por lote/ZIP.
- [x] Tutorial de uso expandido con pasos accionables.
- [x] Consciencia de límites: Spotify como metadata, audio desde fuentes públicas, paginación 50, credenciales y calidad dependiente del origen.
- [x] Ocultar/quitar la FAQ pública "¿Es legal?" para no centrar la landing en riesgo legal.
- [x] FAQ enriquecida con preguntas operativas: cuenta/API, fuente de audio, fallos de match, playlists grandes, idioma, formato y uso móvil.
- [x] Copy SEO con frase objetivo "descargar música de Spotify" usada de forma natural.

### Pendientes opcionales

- [x] Añadir anclas visibles o navegación secundaria hacia Qué es, Características, Tutorial, Límites y FAQ.
- [~] FAQPage schema no implementado: Google lo restringe a sitios gobierno/salud; se añadió `WebPage` schema con `hasPart` para secciones internas.
- [ ] Ajustar copy final con dominio/canonical real cuando deje de ser localhost.

---

## Fase 8 — Features adicionales (backlog priorizado)

### 🔥 Alto impacto

- [ ] **Persistencia de credenciales Spotify por sesión** (cookie/localStorage encriptado) — no pedir al usuario repegar Client ID cada visita
- [ ] **Soporte para Spotify shortlinks** `spotify.link/xyz` (302 redirect a URL real) — los usuarios mobile comparten estos
- [ ] **Sanitización de filenames** para CJK / árabe / emojis (algunos sistemas de archivos rompen)

### ⚡ Medio impacto

- [ ] **Concurrencia configurable** — descargas paralelas (default 3, max 5) ajustable por user
- [ ] **Resume de descargas**: si yt-dlp/pytubefix falla a mitad, reanudar desde byte X (cuando el source lo permite)
- [ ] **Hash check del audio**: SHA256 del archivo descargado mostrado, para verificar integridad
- [x] **ZIP download** del lote completo (mencionado en demo, falta implementar): zip server-side + stream al browser
- [ ] **Drag & drop URL** sobre el input grande del hero
- [x] **Detección automática de paste**: cubierto/priorizado en Fase 5 como auto-búsqueda al ingresar URL válida
- [ ] **Keyboard shortcuts**: `Cmd/Ctrl+V` desde cualquier parte, `Enter` para buscar, `D` para descargar todo
- [ ] **Dark mode toggle** con `prefers-color-scheme` por defecto
- [ ] **i18n ES/EN** mínimo — JSON de strings, switch en footer

### 🌱 Bajo impacto / nice-to-have

- [ ] **PWA**: manifest + service worker para instalar en mobile
- [ ] **Tema "stealth"**: dark mode + sin animaciones, para escritorios corporativos
- [ ] **Embed metadata extra**: BPM, key (extraíble vía librería como `librosa`) — útil para DJs; complementa los metadatos core de Spotify.
- [ ] **Lyrics embed**: si Spotify devuelve lyrics, embeber como tag USLT en el mp3
- [ ] **Soporte para Spotify podcasts** (si la API lo permite) — los episodios suelen tener audio source más limpio
- [ ] **CLI companion**: un `pip install spotify-sing` que use el mismo backend, para integrar en scripts
- [ ] **Webhook on-complete**: para auto-hosted, callback POST cuando un job termina
- [ ] **Telemetría opcional self-hosted** (Plausible/Umami) — sin trackers third-party

---

## Fase 9 — Arquitectura Docker

- [ ] `Dockerfile` para el backend FastAPI (Python 3.11-slim, instalar ffmpeg + pytubefix)
- [ ] `Dockerfile` para el frontend React (build estático servido por nginx)
- [ ] `docker-compose.yml` — servicios: `backend`, `frontend`, volumen `downloads/`
- [ ] Variables de entorno en lugar de `~/.spotifytoyoutube/config.json`:
  - `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET` en `.env`
  - `DOWNLOAD_DIR` → `/app/downloads` (montado como volumen)
- [ ] `ConfigManager` lee env vars con fallback a archivo (para dev local)
- [ ] `.env.example` documentado
- [ ] `README-docker.md` con instrucciones de 3 pasos: clone → copy .env → docker compose up

---

## Fase 10 — Deploy

### Infraestructura

- [ ] `docker compose up -d` levanta todo en puerto 8080
- [ ] Nginx sirve el frontend estático y hace proxy al backend en `/api/`
- [ ] Soporte para reverse proxy (headers `X-Forwarded-For`, etc.)
- [ ] Health check endpoint `GET /health`
- [ ] Logs estructurados (JSON) en el backend para producción
- [ ] Opción: deploy en Fly.io / Railway con un click (Dockerfile ya listo)

### 🛡️ Seguridad / robustez

- [ ] **Rate limiting backend** por IP (10 reqs/min) para auto-hosted públicos
- [ ] **CSRF protection** en endpoints POST (FastAPI middleware)
- [ ] **CORS estricto** — solo dominio configurado, no `*`
- [ ] **Input validation Pydantic estricta** en todos los body params
- [ ] **Filename sanitization** server-side antes de `FileResponse` (path traversal protection)
- [ ] **Limit de tamaño de descarga** por archivo (default 50 MB, configurable)
- [ ] **Auto-cleanup** del `temp_downloads/` cada 30 min para archivos huérfanos (job interrumpido)
- [ ] **Logging sin PII**: nunca loggear el query del usuario completo en producción

### 📊 Observabilidad

- [ ] **Endpoint `/api/stats`**: tracks descargados, errores, success rate (solo admin)
- [ ] **Health checks granulares**: `/health/spotify`, `/health/youtube`, `/health/ffmpeg`
- [ ] **Error tracking opcional** (Sentry self-hosted) — sin datos del usuario, solo stack traces

---

## Referencia técnica — Qué queda, qué se va, qué cambia

| Componente | Estado |
|---|---|
| `src/spotify_client.py` | ✅ Queda igual |
| `src/downloader.py` | ✅ Queda igual |
| `src/config.py` | 🔄 Añadir lectura de env vars (Fase 9) |
| `gui/backend/routes/spotify.py` | ✅ Queda (puede necesitar endpoint `/resolve`) |
| `gui/backend/routes/queue.py` | 🔄 Eliminar ADB, añadir `FileResponse` |
| `gui/backend/routes/config.py` | 🔄 Minor adjustments |
| `gui/backend/routes/adb.py` | ❌ Eliminar |
| `gui/backend/ws_runner.py` | ✅ Queda (logs en tiempo real) |
| `gui/frontend/src/views/CompareView.tsx` | ❌ Eliminar |
| `gui/frontend/src/views/MonitorView.tsx` | ✅ Queda |
| `gui/frontend/src/views/SettingsView.tsx` | 🔄 Quitar campos ADB |
| `gui/frontend/src/components/AdbConnectModal.tsx` | ❌ Eliminar |
| `gui/frontend/src/components/Sidebar.tsx` | 🔄 Reemplazado por `Topbar.tsx` |
| Nueva vista: SearchView / ImportView | 🆕 Crear |
| `Dockerfile` + `docker-compose.yml` | 🆕 Crear (Fase 9) |
