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
  - `SPOTIFY_CONFIG_DIR` → `/app/data` (config.json en volumen persistente — sobrevive redeploys)
  - `ADMIN_DB_PATH` → `/app/data/admin.sqlite3` (DB de admin users/sessions/audit en volumen)
- [x] `ConfigManager.load_config()` lee env vars con prioridad y fallback al archivo (dev local)
- [x] **Persistencia de credenciales Spotify entre redeploys** — `ConfigManager` ahora respeta `SPOTIFY_CONFIG_DIR` / `SPOTIFY_CONFIG_FILE`; el `config.json` vive en `/app/data` (volumen `data:` de docker-compose), no en `~/.spotifytoyoutube`. Si admin guarda credenciales desde `/settings`, sobreviven redeploys sin necesidad de re-setear el env. Env vars siguen teniendo prioridad si están presentes (uso CI/staging).
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

> Implementado round 1 (2026-06-05). Single-admin por ahora; modelo soporta multi-user para futura extensión.

- [x] Tabla `admin_users` (SQLite por defecto, mismo dir que `queue.json` → `data/admin.sqlite3`): columnas `id`, `username` (unique, citext-like lowercase), `password_hash`, `password_algo`, `created_at`, `updated_at`, `last_login_at`, `failed_attempts`, `locked_until`, `totp_secret` (nullable), `is_active`.
- [x] Hash con **Argon2id** (`argon2-cffi`) — params: `time_cost=3`, `memory_cost=65536`, `parallelism=2`. Fallback `bcrypt` (cost 12) si Argon2 no disponible. Nunca SHA/MD5.
- [x] Migración: si `ADMIN_PASSWORD` env existe y tabla vacía, sembrar usuario `admin` con ese password al primer arranque, luego ignorar env en arranques siguientes (loggear `legacy env seed completed`).
- [x] CLI `python -m gui.backend.admin_cli create-user <username>` que pide password por stdin (no argv) + valida fuerza mínima (≥ 12 chars, mezcla clases).
- [x] CLI `reset-password <username>`, `lock <username>`, `unlock <username>`, `list-users`, `rotate-secret`, `revoke-sessions <username>`.
- [x] Eliminar default `"admin"` del fallback en `_admin_password()` — si no hay usuarios en DB y no hay env, devolver 503 en `/admin/login` con mensaje `"Admin not provisioned. Run CLI to create user."`.

### 11.2 — Sesiones firmadas + rotación de secret

> Implementado round 1 (2026-06-05).

- [x] Reemplazar HMAC-SHA256 manual por `itsdangerous.TimestampSigner` o `authlib` con `ADMIN_SESSION_SECRET` obligatorio (≥ 32 bytes random, sin fallback al password).
- [x] Generar `ADMIN_SESSION_SECRET` automático al primer arranque si no existe (guardar en `data/.session_secret` con perms `0600`); rotación manual via CLI invalida todas las sesiones.
- [x] Cookie: añadir `__Host-` prefix cuando `ADMIN_COOKIE_SECURE=1` (fuerza Secure + path=/ + sin Domain), `SameSite=Strict` (no `Lax`) para reducir CSRF cross-site.
- [x] Sesión incluye `user_id`, `issued_at`, `jti` (uuid). Tabla `admin_sessions(jti, user_id, created_at, expires_at, revoked_at, ip_hash, ua_hash)` para revocación server-side.
- [x] Endpoint `POST /admin/logout-all` revoca todas las sesiones del usuario (útil tras sospecha).
- [x] TTL default 24h reducido a **2h** + sliding refresh; idle timeout 30 min.

### 11.3 — Rate-limit y lockout

> Implementado round 1 (2026-06-05). Per-username slowapi omitido — lockout progresivo cubre esa dimensión.

- [x] `slowapi` (FastAPI middleware) — `/admin/login`: **5 intentos / 15 min por IP**. Excede → 429 con `Retry-After`. (Per-username throttling se delega a lockout progresivo de 11.3 punto 2 para evitar duplicación.)
- [x] Lockout progresivo por usuario: 5 fallos consecutivos → `locked_until = now + 15 min`; 10 fallos → 1h; 20 → requiere unlock manual via CLI.
- [x] Respuesta uniforme en login fallido (401 genérico) sin distinguir "user not found" vs "wrong password" — evita user enumeration. Dummy Argon2 verify en path missing-user para flatten timing.
- [x] Delay artificial constante (~200ms) en login para mitigar timing-attacks.

### 11.4 — 2FA TOTP opcional (recomendado para deploy público)

- [ ] `pyotp` para TOTP RFC 6238 (30s window, 6 digits).
- [ ] Flujo enrolamiento: vista `/settings` autenticada muestra QR + secret; user confirma con código antes de activar.
- [ ] Login con 2FA: tras password correcto, retornar `{ "step": "totp" }` + token corto efímero (≤ 5 min, scope=`totp_pending`); segundo POST `/admin/login/totp` con código valida y emite cookie de sesión completa.
- [ ] Backup codes (10 códigos de un uso) generados al activar, mostrados una sola vez, almacenados hasheados.

### 11.5 — Ofuscación de superficie

> Implementado round 3 (2026-06-05). `ADMIN_PATH_PREFIX` diferido — sobre-ingeniería para single-admin y rompe paths hardcoded del SPA. Las otras tres palancas dan 95% del valor.

- [~] ~~Mover ruta de login admin a path no descubrible: `ADMIN_PATH_PREFIX`~~ — diferido. Rompe `/api/admin/*` hardcoded en frontend y CSRF cookie path; coste alto vs beneficio bajo en single-admin self-host.
- [x] Quitar link "Admin" visible en `Footer.tsx` cuando `ADMIN_FOOTER_LINK=false` (env). Default `true` para self-host. `/api/config/public` expone `admin_footer_link`; `Footer.tsx` lo lee y oculta el link.
- [x] `/admin/*` y rutas protegidas (`/config` GET/POST) devuelven **404** (no 401/403) cuando no hay sesión y `ADMIN_STEALTH=true`. `/admin/session` queda 200 (frontend lo necesita para conocer estado de auth) — trade-off documentado. CSRF mismatch también 404 bajo stealth.
- [x] Banner de `Server:` header sobrescrito a `nginx` genérico (implementado round 2 en `SecurityHeadersMiddleware`).

### 11.6 — Endurecimiento de transporte y headers

> Implementado round 2 (2026-06-05). CSP y HSTS opt-in via `SECURITY_HEADERS_STRICT=1` para no romper Vite dev; en Docker default ON.

- [x] Middleware de security headers (manual `SecurityHeadersMiddleware`): `Strict-Transport-Security: max-age=63072000; includeSubDomains; preload`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy: geolocation=(), microphone=(), camera=()`. Header `Server` sobrescrito a `nginx` (no leak de uvicorn version).
- [x] CSP estricta: `default-src 'self'; img-src 'self' https://i.scdn.co data:; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'`.
- [x] Forzar HTTPS redirect cuando `FORCE_HTTPS=1` (honra `X-Forwarded-Proto` para Coolify/Traefik).
- [x] CSRF token sincronizado (double-submit cookie) en todos los `POST /admin/*` salvo `/login`. Frontend `api/client.ts` lee cookie `spotify_sing_csrf` y manda `X-CSRF-Token` automáticamente en POST/PUT/PATCH/DELETE. Aplica también a `POST /config`.

### 11.7 — Audit log

> Implementado round 2 (2026-06-05).

- [x] Tabla `admin_audit(id, ts, user_id, username, ip_hash, ua_hash, action, target, result, meta_json)` con append-only + indices por `ts`, `action`, `user_id`.
- [x] Acciones loggeadas: `login_ok`, `login_fail`, `login_blocked`, `lockout`, `logout`, `logout_all`, `password_change`, `session_revoke`, `csrf_fail`, `config_write`, `audit_view`, `user_lock`, `user_unlock`, `user_create`, `user_delete` (vocab fijo en `audit.ACTIONS`).
- [x] IP y UA almacenados como `sha256(value + ADMIN_META_PEPPER)[:16]` — útil para correlación, no para identificación reversible.
- [x] Endpoint `GET /admin/audit?limit=&since=&action=&user_id=` (paginado, max 1000) para revisión.
- [x] Log a stdout en JSON estructurado además de DB (apto para ingestión Coolify/Loki) — logger `admin.audit` emite línea `{"audit": true, ...}` por evento.

### 11.8 — Encriptación at-rest de credenciales sensibles

> Implementado round 3 (2026-06-05). `totp_secret` diferido hasta 11.4 (sin TOTP aún). `spotify_client_secret` ahora cifrado en `config.json` (no en DB — donde realmente vive el secret).

- [x] `SPOTIFY_CLIENT_SECRET` cifrado at-rest en `config.json` con **Fernet** (AES-128-CBC + HMAC-SHA256, key 32 bytes url-safe base64). Key desde `ADMIN_DATA_KEY` env o auto-gen en `data/.data_key` (perms 0600). `totp_secret` en DB queda pendiente hasta que 11.4 introduzca 2FA.
- [x] Key separada del session secret — `.data_key` ≠ `.session_secret`; distintos blast-radius. Rotación de uno no afecta al otro.
- [x] Helper `gui/backend/admin/crypto.py` — `encrypt(plain) → "v1:<token>"`, `decrypt(blob) → str`, `is_encrypted(blob) → bool`, `try_decrypt(blob)` (no-op si plaintext). Prefijo `v1:` reservado para migración a `v2:` (AES-256-GCM si llega el caso) sin romper datos existentes.
- [x] Migración auto: `ConfigManager.migrate_at_rest_encryption()` invocado en `lifespan`. Detecta secret plaintext en `config.json` (legacy), lo re-encripta in-place y loggea. Idempotente.
- [x] Backups `data/` deben excluir la key: sin `ADMIN_DATA_KEY` env ni `.data_key` archivo, los secrets cifrados son irrecuperables (propiedad deseada). Documentar en runbook de 11.11.

### 11.9 — Validación y abuso

> Implementado round 4 (2026-06-05).

- [x] Pydantic strict mode en `AdminLoginRequest` (`extra="forbid"`, `min_length=1`, `max_length=512` para password, `max_length=64` para username). Regex de username `^[a-z0-9_.-]{3,32}$` aplicada en `users.validate_username`.
- [x] Blocklist de passwords comunes. Lista bundled en `gui/backend/admin/data/common_passwords.txt` (~120 entradas que pasan checks estructurales pero son trivialmente guessable: `Password123!`, `Welcome2025!@`, etc.). Override con env `ADMIN_PWNED_LIST=/path/to/seclists.txt` para cobertura más amplia.
- [x] `AdminGuardMiddleware` cap body en `/api/admin/*` y `/api/config` (default 8 KB, env `ADMIN_BODY_MAX_BYTES`). Retorna 413 (404 bajo stealth).
- [x] `ADMIN_BLOCK_GENERIC_UA=1` rechaza UA vacío / `curl/` / `python-requests/` / `wget/` etc. en `/api/admin/*`. Bypass legítimo: header `X-Admin-Client: <cualquier valor>`. Default off para no romper scripts internos.

### 11.10 — Cookies de YouTube vía login admin (bypass bot detection)

> Implementado round 5 (2026-06-05). Sección embedded en `/settings` en vez de ruta dedicada (menos código, mismo UX).

- [x] Sección protegida en `/settings` (componente `YouTubeCookiesCard` en `SettingsView.tsx`): textarea para pegar `cookies.txt`, toggle "validate live", botones Upload/Delete, status badge.
- [~] ~~Botón "Iniciar sesión con YouTube" OAuth-style~~ — descartado en v1 (Google no expone export de cookies vía API). Upload manual con guía embebida.
- [x] Guía paso a paso embedded (`<details>` collapsible): extensión `Get cookies.txt LOCALLY` → login en cuenta dedicada → export → paste → upload + warning sobre cuenta desechable.
- [x] Backend `POST /admin/youtube-cookies` (JSON `{content, validate_live}`) — parser manual de formato Netscape (`http.cookiejar.Cookie` instances), valida `SID`/`HSID`/`SSID` + uno de `__Secure-3PSID`/`__Secure-1PSID`/`APISID`/`SAPISID`.
- [x] Almacenamiento: cifrado con `crypto.encrypt` (Fernet, reusa key de 11.8) en `data/youtube_cookies.enc`. Metadata separada en `data/youtube_cookies.meta.json` (sin secretos). Plaintext NUNCA toca disco ni logs.
- [x] Integración pytubefix: **monkey-patch** de `pytubefix.request._execute_request` (la lib no acepta `cookies=` en constructor en v10.7). Patch inyecta `Cookie:` header **solo** en URLs `youtube.com` / `googlevideo.com`, idempotente, tagged `_yt_cookies_patched`. Aplica a todos los call-sites de `YouTube()` automáticamente.
- [x] Fallback graceful: `src/downloader.py` cachea bot-detection / consent errors → llama `yt_cookies.mark_invalid(reason)`. Limpia cache header → siguientes requests caen a PO Token only. UI muestra `last_status: invalid:<reason>` en rojo.
- [x] Test de validez `validate_live=true` en upload: `YouTube(test_url, client='WEB').title` con patch instalado. Resultado en `meta.last_status` (`valid` o `invalid:<msg>`).
- [x] `DELETE /admin/youtube-cookies` purga blob + metadata + cache. Audit `youtube_cookies_delete`.
- [x] `GET /admin/youtube-cookies/status` → `{ present, uploaded_at, last_validated_at, last_status }`. Nunca devuelve cookies.
- [x] Warning visible: "dedicated, throwaway YouTube account" en card UI + reminder de sanción potencial.
- [x] Rate-limit upload: `5/hour` por IP via slowapi (`limiter.limit(YT_COOKIES_PER_HOUR)`).
- [x] Audit: `youtube_cookies_upload` / `youtube_cookies_delete` / `youtube_cookies_invalid` añadidos a vocabulario `audit.ACTIONS`. Sin loggear contenido del blob.
- [x] Documentado en `README-docker.md` sección "YouTube cookies (bot-detection bypass)" con guía de export, rotación, y nota de complementariedad con PO Token.

### 11.11 — Documentación + ops

> Implementado round 4 (2026-06-05).

- [x] `README-docker.md` sección "Securing your admin panel" con checklist prod (`ADMIN_SESSION_SECRET`, `ADMIN_DATA_KEY`, `ADMIN_META_PEPPER`, `ADMIN_COOKIE_SECURE=1`, `SECURITY_HEADERS_STRICT=1`, `FORCE_HTTPS=1`, opcionales `ADMIN_STEALTH=1`, `ADMIN_FOOTER_LINK=false`, `ADMIN_BLOCK_GENERIC_UA=1`) + tabla de archivos persistentes + warnings sobre backups.
- [x] `.env.example` reescrito por bloques (rondas 1-4) con comentarios sobre defaults, qué es obligatorio en prod, y comandos de generación.
- [x] Script `tools/check-admin-hardening.py` valida envs, perms POSIX de `.session_secret`/`.data_key`, count de usuarios admin en DB, y reporta `[OK]/[WARN]/[FAIL]`. Flag `--prod` trata `WARN` como `FAIL` (apto para CI). Exit code 0/1.
- [x] Runbook en `README-docker.md` cubre: lost password, unlock user, rotate secret, revoke sessions, inspect audit log, suspected compromise (4 pasos).

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
