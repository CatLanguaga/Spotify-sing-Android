# TODO — Spotify Sync Manager GUI

---

## Hecho ✅

- [x] Explorar y documentar estructura del proyecto existente
- [x] Crear prototipo interactivo → `gui/SpotifySyncManager.html`
- [x] Crear plan de implementación → `plan.md`
- [x] Crear sistema de diseño → `gui/DESIGN.md`
- [x] Crear prompt optimizado para Stitch (enhanced prompt)

---

## Fase 1 — Validar diseño ✅

- [x] Abrir `gui/SpotifySyncManager.html` en el navegador
- [x] Revisar vista Compare: tabla Spotify ↔ Teléfono
- [x] Revisar vista Cola: aprobar / rechazar / buscar alternativa
- [x] Revisar modal YouTube Search
- [x] Revisar vista Monitor: selector de scripts + logs
- [x] Revisar vista Settings: formulario + filtros + blacklist
- [x] Anotar cambios de UX antes de pasar al backend

---

## Fase 2 — Backend FastAPI ✅

- [x] `pip install fastapi uvicorn` en el entorno del proyecto
- [x] Crear `gui/backend/main.py` con la app FastAPI base
- [x] Crear `GET /api/config` — leer `~/.spotifytoyoutube/config.json`
- [x] Crear `POST /api/config` — guardar config
- [x] Crear `GET /api/compare` — ejecutar `smart_compare.py` y retornar JSON
- [x] Crear `GET /api/queue` — cola en memoria (o archivo JSON)
- [x] Crear `PATCH /api/queue/{id}` — aprobar / rechazar item
- [x] Crear `GET /api/youtube/search?q=` — buscar via `youtube_client.py`
- [x] Crear `POST /api/scripts/run` — ejecutar script de `/tools/`
- [x] Crear `WS /ws/logs` — stream de stdout en tiempo real via WebSocket

---

## Fase 3 — Frontend React ✅

- [x] Inicializar proyecto Vite + React + TypeScript en `gui/frontend/`
- [x] Migrar componentes base del prototipo (LangBadge, ScoreBadge, CoverArt, Btn)
- [x] Migrar Sidebar con navegación funcional
- [x] Migrar CompareView — conectar a `GET /api/spotify/playlist/{id}`
- [x] Migrar DownloadQueueView — conectar a `GET/PATCH /api/queue`
- [x] Migrar ProcessMonitorView — conectar WebSocket a `/ws/logs`
- [x] Migrar SettingsView — conectar a `GET/POST /api/config`

---

## Fase 4 — Integración real-time

- [x] Parsear `[X/Y]` en logs para actualizar la barra de progreso real
- [x] YouTubeSearchModal — conectar a `GET /api/youtube/search` desde QueueView
- [x] Auto-refrescar vista Compare cuando termina un script
- [x] Toast notification cuando termina una descarga
- [x] Indicador ADB en sidebar refleja estado real del dispositivo

---

## Fase 4.5 — UX y layout ✅

- [x] Sidebar responsive: 200px con etiquetas en desktop (≥768px), 60px solo íconos en móvil
- [x] Layout corregido para llenar pantalla completa en 1920×1080 (`flex:1` + `minHeight:0` en todas las vistas)
- [x] `GET /api/adb/status` — endpoint real que corre `adb devices` y detecta dispositivo conectado
- [x] Campo **Playlist ID** en Settings — configurable por el usuario, guardado en `config.json`
- [x] CompareView usa el `playlist_id` de Settings en vez de tenerlo hardcodeado
- [x] Control de rango en CompareView: seleccionar tracks N–M de la playlist (ej. 200–330)
- [x] Backend pagina internamente si el rango supera 100 (límite de la Spotify API)
- [x] Columna `#` en tabla de Compare muestra el número de track real dentro de la playlist

---

## Fase 5 — Pulido y empaquetado ✅

- [x] Loading states en todas las vistas (skeleton shimmer en tabla Compare, cards Queue, campos Settings)
- [x] Manejo de errores (error banner con retry en Compare y Queue, banner backend offline en App)
- [x] Confirmación antes de descargar N tracks (modal con conteo de tracks aprobados)
- [x] Arranque automático del browser al correr `python gui/backend/main.py`
- [x] Búsqueda automática de dispositivo Android (polling ADB cada 5s + modal de confirmación con modelo y serial)
- [ ] (Opcional) Empaquetar como app de escritorio con Tauri

---

## Referencia rápida

| Archivo | Qué es |
|---|---|
| `gui/SpotifySyncManager.html` | Prototipo interactivo (abrir en browser) |
| `gui/DESIGN.md` | Sistema de diseño completo |
| `plan.md` | Plan detallado con arquitectura y stack |
| `gui/backend/main.py` | Servidor FastAPI |
| `gui/frontend/` | App React/Vite (Vite dev server en localhost:5173) |
