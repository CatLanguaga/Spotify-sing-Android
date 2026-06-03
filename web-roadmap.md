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
| 8 — Features adicionales | ⏭️ Pospuesta | backlog; saltada para priorizar deploy |
| 9 — Arquitectura Docker | ✅ Completa | single-container (multi-stage Dockerfile) + env vars + compose; pendiente build real con Docker |
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

- [x] Sección "Qué es esta página" con definición clara de Mp3vine y su flujo real.
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

- [x] **Idioma principal de la página en inglés** — landing, navegación, CTA, estados, FAQ, SEO meta y `<html lang="en">`
- [x] **Autenticación admin mínima** — sesión cookie HTTP-only firmada para identificar administradores antes de mostrar vistas sensibles
- [x] **Configuración solo para administradores** — link oculto a usuarios no-admin y rutas/API de config protegidas en backend
- [x] **Persistencia de credenciales Spotify** — credenciales guardadas server-side en config/env y editables solo con sesión admin; no se exponen a usuarios públicos
- [x] **Soporte para Spotify shortlinks** `spotify.link/xyz` / `spotify.app.link/xyz` — resuelve redirect a URL real y valida destino Spotify
- [x] **Sanitización de filenames** para CJK / árabe / emojis (algunos sistemas de archivos rompen)

### ⚡ Medio impacto

- [x] **Concurrencia configurable** — descargas paralelas (default 3, max 5) ajustable por admin; backend usa gate dinámico y frontend usa `/config/public`
- [~] **Resume de descargas**: `pytubefix` no expone byte-offset explícito; se activó `skip_existing=true` + `max_retries=2` como recuperación best-effort cuando el source/librería lo permite
- [x] **Hash check del audio**: SHA256 calculado al terminar descarga y mostrado en cada track descargado
- [x] **ZIP download** del lote completo (mencionado en demo, falta implementar): zip server-side + stream al browser
- [x] **Drag & drop URL** sobre el input grande del hero
- [x] **Detección automática de paste**: cubierto/priorizado en Fase 5 como auto-búsqueda al ingresar URL válida
- [x] **Keyboard shortcuts**: `Cmd/Ctrl+V` desde cualquier parte enfoca input, `Enter` busca, `D` descarga todo visible
- [x] **Dark mode toggle** con `prefers-color-scheme` por defecto
- [x] **i18n ES/EN opcional** — provider de strings + switch en footer; navegación/hero/footer conectados

### 🌱 Bajo impacto / nice-to-have

- [ ] **PWA**: manifest + service worker para instalar en mobile
- [x] **Tema "stealth"**: dark mode + sin animaciones, para escritorios corporativos
- [x] **Embed metadata extra**: BPM, key (extraíble vía librería como `librosa`) — útil para DJs; complementa los metadatos core de Spotify.
- [x] **Lyrics embed**: si Spotify devuelve lyrics, embeber como tag USLT en el mp3; M4A/OPUS también reciben tag de lyrics equivalente
- [ ] **Soporte para Spotify podcasts** (si la API lo permite) — los episodios suelen tener audio source más limpio
- [ ] **CLI companion**: un `pip install spotify-sing` que use el mismo backend, para integrar en scripts
- [ ] **Webhook on-complete**: para auto-hosted, callback POST cuando un job termina
- [ ] **Telemetría opcional self-hosted** (Plausible/Umami) — sin trackers third-party

### 🧭 Pendientes detectados tras QA

- [ ] **Detección automática de idioma del usuario** — usar navegador/locale/IP opcional para escoger idioma inicial; respetar override manual en `localStorage`
- [x] **Cambio de idioma completo y correcto** — `preferences.tsx` ahora expone diccionario EN/ES completo; topbar, hero, tutorial, FAQ, PlaylistCard, TrackRow, TrackPaginator, QuickTrackModal, ManualSearchModal, SettingsView, footer, SEO meta (`seo.ts` con title/description bilingüe) y toasts usan `t()`
- [ ] **Automatizar temas** — permitir modo automático por `prefers-color-scheme`, mantener override manual y documentar ciclo Light/Dark/Stealth
- [ ] **Corregir layout del tutorial** — actualmente queda con zonas en blanco y se descuadra; rehacer espaciado, grid, anchos y responsive
- [ ] **Reducir exceso de iconos** — simplificar UI, usar iconos solo donde aporten claridad y mantener botones legibles
- [x] **Acceso sencillo a credenciales/admin** — link "Admin" visible en footer apunta a `/settings`, que ya renderiza form de login si no hay sesión; descubrimiento sin exponer secretos
- [x] **Páginas legales** — `/terms` y `/privacy` con contenido bilingüe (EN/ES) modelado tras spotisaver: scope, no afiliación, responsabilidad del usuario, garantías, takedown, datos mínimos, cookie admin
- [x] **Disclaimer en footer** — footer muestra "Not affiliated with Spotify AB." / "Sin afiliación con Spotify AB." sin claims extra

---

## Fase 9 — Arquitectura Docker

> Implementada 2026-06-01 como **single-container** (decisión: más simple para Coolify; FastAPI ya monta el SPA en `/`). Credenciales **env-var single-tenant**.

- [x] `Dockerfile` multi-stage: stage `node:20-slim` build del SPA → stage `python:3.11-slim` con `ffmpeg` que sirve `dist/` + `/api`
- [~] ~~`Dockerfile` frontend nginx separado~~ — N/A: el backend FastAPI sirve el estático (un solo servicio/puerto 8000)
- [x] `docker-compose.yml` — servicio `app`, volúmenes `downloads`/`data`, healthcheck
- [x] Variables de entorno en lugar de `~/.spotifytoyoutube/config.json`:
  - `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET` (prioridad sobre el archivo)
  - `DOWNLOAD_DIR` → `/app/downloads`; `SPOTIFY_QUEUE_FILE` → `/app/data/queue.json`
- [x] `ConfigManager.load_config()` lee env vars con prioridad y fallback al archivo (dev local)
- [x] `requirements-docker.txt` ligero (sin pywebview / google-api-python-client)
- [x] Frontend `API_BASE` relativo (`/api`) fuera de Vite dev — funciona tras proxy/SSL de Coolify
- [x] `/health` endpoint + Docker `HEALTHCHECK`
- [x] `.env.example` documentado
- [x] `README-docker.md` con instrucciones de 3 pasos + sección Coolify
- [ ] Build/run real con Docker (no disponible en esta máquina) — pendiente verificar en host con Docker o directo en Coolify

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

## Fase 11 — Hardening de seguridad admin

> Motivación: el flujo actual de admin (`gui/backend/routes/admin.py`) usa password único en env (`ADMIN_PASSWORD`), default `"admin"` si no se configura, sin rate-limit, sin lockout, sin usuario en DB, sin rotación de secret, sin 2FA. Bastan curiosidad + diccionario para entrar. Esta fase eleva el coste de ataque y aísla el panel sensible.

### 11.1 — Modelo de usuario admin en DB

- [ ] Tabla `admin_users` (SQLite por defecto, mismo dir que `queue.json` → `data/admin.sqlite3`): columnas `id`, `username` (unique, citext-like lowercase), `password_hash`, `password_algo`, `created_at`, `updated_at`, `last_login_at`, `failed_attempts`, `locked_until`, `totp_secret` (nullable), `is_active`.
- [ ] Hash con **Argon2id** (`argon2-cffi`) — params: `time_cost=3`, `memory_cost=65536`, `parallelism=2`. Fallback `bcrypt` (cost 12) si Argon2 no disponible. Nunca SHA/MD5.
- [ ] Migración: si `ADMIN_PASSWORD` env existe y tabla vacía, sembrar usuario `admin` con ese password al primer arranque, luego ignorar env en arranques siguientes (loggear `legacy env seed completed`).
- [ ] CLI `python -m gui.backend.admin_cli create-user <username>` que pide password por stdin (no argv) + valida fuerza mínima (≥ 12 chars, mezcla clases).
- [ ] CLI `reset-password <username>`, `lock <username>`, `unlock <username>`, `list-users`.
- [ ] Eliminar default `"admin"` del fallback en `_admin_password()` — si no hay usuarios en DB y no hay env, devolver 503 en `/admin/login` con mensaje `"Admin not provisioned. Run CLI to create user."`.

### 11.2 — Sesiones firmadas + rotación de secret

- [ ] Reemplazar HMAC-SHA256 manual por `itsdangerous.TimestampSigner` o `authlib` con `ADMIN_SESSION_SECRET` obligatorio (≥ 32 bytes random, sin fallback al password).
- [ ] Generar `ADMIN_SESSION_SECRET` automático al primer arranque si no existe (guardar en `data/.session_secret` con perms `0600`); rotación manual via CLI invalida todas las sesiones.
- [ ] Cookie: añadir `__Host-` prefix cuando `ADMIN_COOKIE_SECURE=1` (fuerza Secure + path=/ + sin Domain), `SameSite=Strict` (no `Lax`) para reducir CSRF cross-site.
- [ ] Sesión incluye `user_id`, `issued_at`, `jti` (uuid). Tabla `admin_sessions(jti, user_id, created_at, expires_at, revoked_at, ip_hash, ua_hash)` para revocación server-side.
- [ ] Endpoint `POST /admin/logout-all` revoca todas las sesiones del usuario (útil tras sospecha).
- [ ] TTL default 24h reducido a **2h** + sliding refresh; idle timeout 30 min.

### 11.3 — Rate-limit y lockout

- [ ] `slowapi` (FastAPI middleware) — `/admin/login`: **5 intentos / 15 min por IP** + **10 / hora por username**. Excede → 429 con `Retry-After`.
- [ ] Lockout progresivo por usuario: 5 fallos consecutivos → `locked_until = now + 15 min`; 10 fallos → 1h; 20 → requiere unlock manual via CLI.
- [ ] Respuesta uniforme en login fallido (401 genérico) sin distinguir "user not found" vs "wrong password" — evita user enumeration.
- [ ] Delay artificial constante (~200ms) en login para mitigar timing-attacks.

### 11.4 — 2FA TOTP opcional (recomendado para deploy público)

- [ ] `pyotp` para TOTP RFC 6238 (30s window, 6 digits).
- [ ] Flujo enrolamiento: vista `/settings` autenticada muestra QR + secret; user confirma con código antes de activar.
- [ ] Login con 2FA: tras password correcto, retornar `{ "step": "totp" }` + token corto efímero (≤ 5 min, scope=`totp_pending`); segundo POST `/admin/login/totp` con código valida y emite cookie de sesión completa.
- [ ] Backup codes (10 códigos de un uso) generados al activar, mostrados una sola vez, almacenados hasheados.

### 11.5 — Ofuscación de superficie

- [ ] Mover ruta de login admin a path no descubrible: env `ADMIN_PATH_PREFIX` (default `/admin`), si configurado a `/_x/<token>` el resto del montaje sigue ese prefix. **No seguridad por oscuridad sola** — capa adicional, no reemplazo de auth.
- [ ] Quitar link "Admin" visible en `Footer.tsx` cuando `ADMIN_FOOTER_LINK=false` (env). Default `true` para self-host, `false` recomendado prod público.
- [ ] `/admin/*` y `/settings` devuelven **404 idéntico al de SPA** (no 401) cuando no hay sesión y `ADMIN_STEALTH=true` — el atacante no confirma existencia del panel.
- [ ] Banner de `Server:` header eliminado / sobrescrito a `nginx` genérico para no filtrar uvicorn + version.

### 11.6 — Endurecimiento de transporte y headers

- [ ] Middleware de security headers (`secure` lib o manual): `Strict-Transport-Security: max-age=63072000; includeSubDomains; preload`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy: geolocation=(), microphone=(), camera=()`.
- [ ] CSP estricta: `default-src 'self'; img-src 'self' https://i.scdn.co data:; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'`.
- [ ] Forzar HTTPS redirect cuando `FORCE_HTTPS=1`.
- [ ] CSRF token sincronizado (double-submit cookie) en todos los `POST /admin/*` salvo `/login` (que ya es origen del session-set).

### 11.7 — Audit log

- [ ] Tabla `admin_audit(id, ts, user_id, ip_hash, action, target, result, meta_json)` con append-only.
- [ ] Acciones loggeadas: `login_ok`, `login_fail`, `lockout`, `password_change`, `totp_enable`, `totp_disable`, `config_write`, `session_revoke`, `user_create`, `user_delete`.
- [ ] IP y UA almacenados como `sha256(value + per-install-pepper)[:16]` — útil para correlación, no para identificación reversible.
- [ ] Endpoint `GET /admin/audit?limit=&since=` (paginado) para revisión.
- [ ] Log a stdout en JSON estructurado además de DB (apto para ingestión Coolify/Loki).

### 11.8 — Encriptación at-rest de credenciales sensibles

- [ ] `SPOTIFY_CLIENT_SECRET` y `totp_secret` cifrados en DB con AES-256-GCM (key derivada de `ADMIN_DATA_KEY` env, ≥ 32 bytes). `cryptography.fernet` aceptable como alternativa.
- [ ] Key separada del session secret — distintos blast-radius.
- [ ] Helper `crypto.encrypt(plaintext) → bytes`, `crypto.decrypt(blob) → str` con versión de algoritmo prefijada para migraciones futuras.
- [ ] Backups `data/*.sqlite3` excluyen exportar la key; documentar que sin `ADMIN_DATA_KEY` el backup es inútil (propiedad deseada).

### 11.9 — Validación y abuso

- [ ] Pydantic strict mode en todos los body de `/admin/*` (`extra="forbid"`, longitudes máximas, regex de username `^[a-z0-9_.-]{3,32}$`).
- [ ] Rechazar passwords del top-10k de `haveibeenpwned` (lista local descargada en build, no API externa).
- [ ] Limitar tamaño body `/admin/*` a 8 KB (middleware).
- [ ] Bloquear `User-Agent` vacío o `curl`/`python-requests` sin header custom en `/admin/*` (heurística suave; activable por env).

### 11.10 — Documentación + ops

- [ ] `README-docker.md`: sección "Securing your admin panel" con checklist de envs obligatorias en producción (`ADMIN_SESSION_SECRET`, `ADMIN_DATA_KEY`, `ADMIN_COOKIE_SECURE=1`, `FORCE_HTTPS=1`, `ADMIN_STEALTH=true`, `ADMIN_FOOTER_LINK=false`).
- [ ] `.env.example` actualizado con los nuevos vars + comentarios `# REQUIRED in production`.
- [ ] Script `tools/check-admin-hardening.py` que valida envs, perms de `data/.session_secret`, presencia de usuario admin, y reporta semáforo verde/ámbar/rojo.
- [ ] Runbook breve: cómo rotar secret, cómo unlockear usuario, cómo revocar sesiones tras compromiso.

### Prioridad sugerida

1. **11.1 + 11.2 + 11.3** — base imprescindible (DB user, Argon2, rate-limit, no default password).
2. **11.6 + 11.7** — headers + audit log (bajo coste, alto valor forense).
3. **11.5 + 11.8** — stealth + encriptación at-rest (refuerza si deploy público).
4. **11.4** — 2FA TOTP (opcional, recomendado para multi-admin).
5. **11.9 + 11.10** — pulido + ops.

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
