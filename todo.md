# TODO — Spotify Sync Manager GUI

---

## Hecho ✅

- [x] Explorar y documentar estructura del proyecto existente
- [x] Crear prototipo interactivo → `gui/SpotifySyncManager.html`
- [x] Crear plan de implementación → `plan.md`
- [x] Crear sistema de diseño → `gui/DESIGN.md`
- [x] Crear prompt optimizado para Stitch (enhanced prompt)

---

## Fase 1 — Validar diseño

- [ ] Abrir `gui/SpotifySyncManager.html` en el navegador
- [ ] Revisar vista Compare: tabla Spotify ↔ Teléfono
- [ ] Revisar vista Cola: aprobar / rechazar / buscar alternativa
- [ ] Revisar modal YouTube Search
- [ ] Revisar vista Monitor: selector de scripts + logs
- [ ] Revisar vista Settings: formulario + filtros + blacklist
- [ ] Anotar cambios de UX antes de pasar al backend

---

## Fase 2 — Backend FastAPI

- [ ] `pip install fastapi uvicorn` en el entorno del proyecto
- [ ] Crear `gui/backend/main.py` con la app FastAPI base
- [ ] Crear `GET /api/config` — leer `~/.spotifytoyoutube/config.json`
- [ ] Crear `POST /api/config` — guardar config
- [ ] Crear `GET /api/compare` — ejecutar `smart_compare.py` y retornar JSON
- [ ] Crear `GET /api/queue` — cola en memoria (o archivo JSON)
- [ ] Crear `PATCH /api/queue/{id}` — aprobar / rechazar item
- [ ] Crear `GET /api/youtube/search?q=` — buscar via `youtube_client.py`
- [ ] Crear `POST /api/scripts/run` — ejecutar script de `/tools/`
- [ ] Crear `WS /ws/logs` — stream de stdout en tiempo real via WebSocket

---

## Fase 3 — Frontend React

- [ ] Inicializar proyecto Vite + React + TypeScript en `gui/frontend/`
- [ ] Migrar componentes base del prototipo (LangBadge, ScoreBadge, CoverArt, Btn)
- [ ] Migrar Sidebar con navegación funcional
- [ ] Migrar CompareView — conectar a `GET /api/compare`
- [ ] Migrar DownloadQueueView — conectar a `GET/PATCH /api/queue`
- [ ] Migrar YouTubeSearchModal — conectar a `GET /api/youtube/search`
- [ ] Migrar ProcessMonitorView — conectar WebSocket a `/ws/logs`
- [ ] Migrar SettingsView — conectar a `GET/POST /api/config`

---

## Fase 4 — Integración real-time

- [ ] Parsear `[X/Y]` en logs para actualizar la barra de progreso real
- [ ] Auto-refrescar vista Compare cuando termina un script
- [ ] Toast notification cuando termina una descarga
- [ ] Indicador ADB en sidebar refleja estado real del dispositivo

---

## Fase 5 — Pulido y empaquetado

- [ ] Loading states en todas las vistas (skeleton / spinner)
- [ ] Manejo de errores (API caída, ADB desconectado, rate limit YouTube)
- [ ] Confirmación antes de descargar N tracks
- [ ] Arranque automático del browser al correr `python gui/backend/main.py`
- [ ] (Opcional) Empaquetar como app de escritorio con Tauri

---

## Referencia rápida

| Archivo | Qué es |
|---|---|
| `gui/SpotifySyncManager.html` | Prototipo interactivo (abrir en browser) |
| `gui/DESIGN.md` | Sistema de diseño completo |
| `plan.md` | Plan detallado con arquitectura y stack |
| `gui/backend/main.py` | (por crear) Servidor FastAPI |
| `gui/frontend/` | (por crear) App React/Vite |
