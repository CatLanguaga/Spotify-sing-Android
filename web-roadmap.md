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
