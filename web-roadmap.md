# Web Roadmap — Spotify Downloader Portal

**Objetivo:** Convertir esta app de escritorio en un portal web Docker-friendly para descargar música de Spotify directo al dispositivo del usuario. Sin ADB, sin comparación con teléfono.

**Referentes UX:**
- [cobalt.tools](https://cobalt.tools) — input único, proceso inmediato, minimalismo radical
- [metube](https://github.com/alexta69/metube) — queue visual, progreso en tiempo real, auto-download al browser
- [Exportify](https://exportify.net) — login Spotify OAuth, grid de playlists, UX limpia
- [spotDL web](https://github.com/spotDL/spotify-downloader) — mismo core técnico

---

## Fase 0 — Arquitectura Docker

- [ ] `Dockerfile` para el backend FastAPI (Python 3.11-slim, instalar ffmpeg + yt-dlp)
- [ ] `Dockerfile` para el frontend React (build estático servido por nginx)
- [ ] `docker-compose.yml` — servicios: `backend`, `frontend`, volumen `downloads/`
- [ ] Variables de entorno en lugar de `~/.spotifytoyoutube/config.json`:
  - `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET` en `.env`
  - `DOWNLOAD_DIR` → `/app/downloads` (montado como volumen)
- [ ] `ConfigManager` lee env vars con fallback a archivo (para dev local)
- [ ] `.env.example` documentado
- [ ] `README-docker.md` con instrucciones de 3 pasos: clone → copy .env → docker compose up

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

El flujo cambia: el servidor descarga el archivo → el browser lo recibe automáticamente.

- [x] Nuevo endpoint `GET /api/queue/{item_id}/file` — sirve el archivo descargado como `FileResponse` con `Content-Disposition: attachment`
- [x] El frontend hace `window.location.href = /api/queue/{id}/file` tras descarga exitosa → browser descarga el archivo
- [x] Limpieza automática: borrar archivo del servidor X minutos después de servido (evitar llenado de disco)
- [x] Endpoint `POST /api/download/direct` — recibe URL de Spotify o playlist, retorna job_id inmediatamente, procesa en background
- [x] `GET /api/download/{job_id}/status` — polling de estado (o WebSocket ya existente)
- [x] Validar que `yt-dlp` y `ffmpeg` están disponibles en Docker antes de aceptar solicitudes (nota: proyecto usa `pytubefix` en lugar de `yt-dlp`; se valida `pytubefix` + `ffmpeg`)

---

## Fase 3 — Frontend: rediseño web-first

### Vista principal — Search / Import

> Inspiración: cobalt.tools. Una sola acción domina la pantalla.

- [ ] Hero con input grande: pegar URL de Spotify (track, álbum, o playlist)
- [ ] Validación en tiempo real: detectar tipo (track / album / playlist) y mostrarlo con ícono
- [ ] Botón "Importar" → llama `GET /api/spotify/resolve?url=` → muestra resultados
- [ ] Estado vacío elegante con instrucciones y ejemplos de URLs válidas

### Vista de Playlist / Álbum

> Inspiración: Exportify (grid de tracks), metube (selección múltiple).

- [ ] Header con cover art grande, nombre de playlist, total de tracks, duración total
- [ ] Tabla de tracks: cover (40px), título, artista, duración, idioma badge, checkbox
- [ ] Selección múltiple: checkbox por fila + "Seleccionar todos" en header
- [ ] Barra inferior sticky: `N tracks seleccionados · Formato [mp3▾] · Calidad [320▾] · [Agregar a cola]`
- [ ] Filtro por texto (nombre/artista) + filtro por idioma
- [ ] Paginación o scroll infinito para playlists grandes

### Vista de Cola (Queue)

> Inspiración: metube. Cards con progreso, auto-descarga al terminar.

- [ ] Cards compactas: cover, título, artista, formato/calidad, estado, barra de progreso
- [ ] Estados: `pendiente → buscando YT → descargando → listo ✓ / error ✗`
- [ ] Al llegar a "listo": botón "⬇ Descargar" + descarga automática via browser
- [ ] Botón de retry en cards de error
- [ ] "Descargar todos listos" — batch download de todos los archivos completados
- [ ] Contador de progreso batch: `(3 / 8) descargando...`
- [ ] Botón "Limpiar completados"

### Vista de Configuración

- [ ] Campos: Spotify Client ID, Spotify Client Secret (con link a developer.spotify.com)
- [ ] Formato por defecto (mp3 / m4a / opus) y calidad (128 / 192 / 320 kbps)
- [ ] Test de conexión Spotify: botón "Verificar credenciales"
- [ ] Sin campos de ADB, sin carpeta de descarga (no aplica en web)
- [ ] Info sobre cómo crear una Spotify App con pasos visuales

### Sidebar / Navegación

- [ ] Items: **Inicio** (search/import), **Cola**, **Configuración**
- [ ] Sin item "Compare" ni indicadores ADB
- [ ] Badge en "Cola" con count de items pendientes
- [ ] Logo + nombre de la app arriba

---

## Fase 4 — UX Polish

### Flujo rápido (single-track)

- [ ] Para URLs de track individual: saltarse playlist view, ir directo a cola con el track pre-cargado
- [ ] Modal de confirmación mínimo: formato + calidad + "Descargar ahora"

### YouTube matching

- [ ] El backend busca YT automáticamente al agregar a cola (ya existe parcialmente)
- [ ] Si el match tiene score < 65%: mostrar modal de revisión con 3 opciones alternativas
- [ ] El usuario puede buscar manualmente si ninguna opción convence

### Feedback visual

- [ ] Toast notifications para: track agregado a cola, descarga lista, error
- [ ] Skeleton loaders en playlist view mientras carga
- [ ] Animación de progreso real (parsear `[X/Y]` del output de yt-dlp via WebSocket)

### Responsive / Mobile

- [ ] La app debe funcionar en móvil (descargar desde el teléfono)
- [ ] Sidebar colapsa a bottom navigation en mobile
- [ ] Cards de cola apiladas, touch-friendly (48px min tap targets)
- [ ] Input de URL acepta Share desde Spotify mobile

---

## Fase 5 — Deploy

- [ ] `docker compose up -d` levanta todo en puerto 8080
- [ ] Nginx sirve el frontend estático y hace proxy al backend en `/api/`
- [ ] Soporte para reverse proxy (headers `X-Forwarded-For`, etc.)
- [ ] Health check endpoint `GET /health`
- [ ] Logs estructurados (JSON) en el backend para producción
- [ ] Opción: deploy en Fly.io / Railway con un click (Dockerfile ya listo)

---

## Fase 6 — UX de visualización: límite + range slider dinámico

> Decisión de diseño confirmada (2026-05-26): pivot a single-page, sin cola persistente. Resultados inline, descarga directa. Ver `gui/design-demos/demo-singlepage.html`.

### Límite de 50 tracks por consulta

- [ ] Constante backend `MAX_TRACKS_PER_REQUEST = 50` en `src/config.py` o env var
- [ ] `GET /api/spotify/resolve?url=&offset=&limit=` — siempre `limit ≤ 50`
- [ ] Backend ignora `limit > 50` y aplica clamp silencioso
- [ ] Si `playlist.total > 50`: response incluye `total`, `returned`, `offset` — el frontend renderiza el slider
- [ ] Cache de metadata Spotify por `playlist_id` (TTL 10 min) para no repegar a Spotify API cuando el usuario mueve el slider

### Range slider dinámico (frontend)

- [ ] Componente `<TrackRangeSlider />` con 2 handles (from / to)
- [ ] Restricciones: `to - from ≤ 50`, `from ≥ 1`, `to ≤ playlist.total`
- [ ] Al mover un handle: si la ventana intenta crecer > 50, el handle opuesto se desplaza automáticamente manteniendo `width = 50` (modo "ventana deslizante")
- [ ] Modo "compactar": el usuario puede arrastrar el centro de la ventana para moverla completa sin cambiar el ancho
- [ ] Visual: barra horizontal con marks cada 10, ventana resaltada en verde Spotify, texto `Mostrando 51–100 de 247`
- [ ] Debounce 300 ms al refetch (`/api/spotify/resolve?offset=X&limit=Y`)
- [ ] Estado URL: `?range=51-100` para deep-link / share
- [ ] Botones rápidos: `[Primeras 50] [Siguientes 50] [Últimas 50]`

### Edge cases

- [ ] Playlist ≤ 50: ocultar slider, mostrar todo
- [ ] Track individual / álbum < 50: sin slider
- [ ] Loading skeleton mientras refetch (no parpadeo de tabla)
- [ ] Persistir última ventana en `localStorage` por `playlist_id`

---

## Fase 7 — SEO + estructura de página

> Pendiente: el usuario aportará skills específicas con detalles. Placeholder de items esperables abajo.

### Meta + structured data

- [ ] `<title>`, `<meta description>`, `<meta og:*>`, `<meta twitter:*>` dinámicos por vista
- [ ] `<link rel="canonical">` correcto
- [ ] JSON-LD `WebApplication` schema en home
- [ ] `robots.txt` + `sitemap.xml` (rutas `/`, `/how-it-works`, `/faq`)
- [ ] `<html lang="es">` + atributo `lang` por sección si hay multi-idioma

### Performance / Core Web Vitals

- [ ] Lazy-load de covers (`loading="lazy"`)
- [ ] Preconnect a Spotify CDN (`i.scdn.co`)
- [ ] Fonts: `font-display: swap` + subset preload
- [ ] Inline critical CSS, defer no-critical
- [ ] LCP < 2.5s, CLS < 0.1, INP < 200ms — verificar con Lighthouse

### Estructura semántica

- [ ] `<header>`, `<main>`, `<section>`, `<footer>` correctos
- [ ] Heading hierarchy sin saltos (h1 → h2 → h3)
- [ ] `<details>/<summary>` para FAQ (ya implementado en demo)
- [ ] ARIA labels en botones de descarga e input principal
- [ ] Focus rings visibles, navegación por teclado completa
- [ ] Skip-link "Saltar al contenido"

### Accesibilidad WCAG AA mínimo

- [ ] Contraste texto ≥ 4.5:1 (verificar acento verde sobre blanco)
- [ ] `prefers-reduced-motion` respetado en animaciones
- [ ] `aria-live` para estados de descarga (lector de pantalla anuncia "descargado")
- [ ] Labels asociados a todos los inputs (`<label for>`)

---

## Fase 8 — Mejorar matching YouTube (reducir errores y descargas erróneas)

### Scoring del match

- [ ] Algoritmo de score considera: duración (±3s del Spotify duration), artista normalizado (lowercase, sin features), título normalizado (quitar `(Official Video)`, `[MV]`, `Lyric Video`, etc.), año, canal verificado
- [ ] Threshold mínimo: si `score < 65` no auto-descarga, abre modal de revisión con top 3 alternativas
- [ ] Threshold óptimo: si `score ≥ 90` auto-descarga sin confirmación

### Estrategias de búsqueda

- [ ] Query primaria: `"Artista" "Título" topic` (canales "Topic" de YouTube son re-uploads oficiales del label, suelen ser exactos)
- [ ] Fallback 1: `"Artista" "Título" audio` (excluye videos)
- [ ] Fallback 2: `"Artista" "Título" lyrics` (suele ser audio limpio)
- [ ] Fallback 3: query simple sin comillas
- [ ] Filtrar resultados con duración fuera de ±10s del track Spotify
- [ ] Penalizar canales con palabras flag: `cover`, `remix`, `karaoke`, `8d`, `slowed`, `sped up`, `nightcore`, `live` (a menos que el track Spotify ya sea live)

### Manual override

- [ ] Botón "Buscar manualmente" en cada track → modal con search bar YouTube + preview embeds
- [ ] Botón "Pegar URL de YouTube" para forzar source específico
- [ ] Persistir overrides exitosos por `spotify_id` en cache local (si el usuario corrigió un track, recordarlo)

### Calidad del audio source

- [ ] Preferir streams con bitrate más alto disponible (ya implementado parcialmente)
- [ ] Si el bitrate del source < bitrate destino solicitado: warning visible al usuario
- [ ] Detectar y rechazar streams "music" cortos (intros, sketches) por duración

---

## Fase 9 — Sugerencias adicionales (priorizadas)

### 🔥 Alto impacto

- [ ] **Persistencia de credenciales Spotify por sesión** (cookie/localStorage encriptado) — no pedir al usuario repegar Client ID cada visita
- [ ] **Soporte para Spotify shortlinks** `spotify.link/xyz` (302 redirect a URL real) — los usuarios mobile comparten estos
- [ ] **Rate limiting backend** por IP (10 reqs/min) para auto-hosted públicos
- [ ] **Caché de búsqueda YouTube** por `spotify_id` — si 5 usuarios piden el mismo track, no buscamos 5 veces
- [ ] **Detección de geo-restricción YouTube**: si el track falla por región, sugerir VPN o source alternativo
- [ ] **Sanitización de filenames** para CJK / árabe / emojis (algunos sistemas de archivos rompen)

### ⚡ Medio impacto

- [ ] **Concurrencia configurable** — descargas paralelas (default 3, max 5) ajustable por user
- [ ] **Resume de descargas**: si yt-dlp/pytubefix falla a mitad, reanudar desde byte X (cuando el source lo permite)
- [ ] **Hash check del audio**: SHA256 del archivo descargado mostrado, para verificar integridad
- [ ] **ZIP download** del lote completo (mencionado en demo, falta implementar): zip server-side + stream al browser
- [ ] **Drag & drop URL** sobre el input grande del hero
- [ ] **Detección automática de paste**: si el usuario pega URL válida, auto-submit sin click
- [ ] **Keyboard shortcuts**: `Cmd/Ctrl+V` desde cualquier parte, `Enter` para buscar, `D` para descargar todo
- [ ] **Dark mode toggle** con `prefers-color-scheme` por defecto
- [ ] **i18n ES/EN** mínimo — JSON de strings, switch en footer
- [ ] **Progress bar realista** vía WebSocket (ya existe `ws_runner`) — parsea `[X/Y]` de pytubefix/ffmpeg

### 🌱 Bajo impacto / nice-to-have

- [ ] **PWA**: manifest + service worker para instalar en mobile
- [ ] **Tema "stealth"**: dark mode + sin animaciones, para escritorios corporativos
- [ ] **Embed metadata extra**: BPM, key (extraíble vía librería como `librosa`) — útil para DJs
- [ ] **Lyrics embed**: si Spotify devuelve lyrics, embeber como tag USLT en el mp3
- [ ] **Soporte para Spotify podcasts** (si la API lo permite) — los episodios suelen tener audio source más limpio
- [ ] **CLI companion**: un `pip install spotify-sing` que use el mismo backend, para integrar en scripts
- [ ] **Webhook on-complete**: para auto-hosted, callback POST cuando un job termina
- [ ] **Telemetría opcional self-hosted** (Plausible/Umami) — sin trackers third-party

### 🛡️ Seguridad / robustez

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
| `src/config.py` | 🔄 Añadir lectura de env vars |
| `gui/backend/routes/spotify.py` | ✅ Queda (puede necesitar endpoint `/resolve`) |
| `gui/backend/routes/queue.py` | 🔄 Eliminar ADB, añadir `FileResponse` |
| `gui/backend/routes/config.py` | 🔄 Minor adjustments |
| `gui/backend/routes/adb.py` | ❌ Eliminar |
| `gui/backend/ws_runner.py` | ✅ Queda (logs en tiempo real) |
| `gui/frontend/src/views/CompareView.tsx` | ❌ Eliminar |
| `gui/frontend/src/views/MonitorView.tsx` | ✅ Queda |
| `gui/frontend/src/views/SettingsView.tsx` | 🔄 Quitar campos ADB |
| `gui/frontend/src/components/AdbConnectModal.tsx` | ❌ Eliminar |
| `gui/frontend/src/components/Sidebar.tsx` | 🔄 Quitar ADB indicator, quitar Compare |
| Nueva vista: SearchView / ImportView | 🆕 Crear |
| `Dockerfile` + `docker-compose.yml` | 🆕 Crear |
