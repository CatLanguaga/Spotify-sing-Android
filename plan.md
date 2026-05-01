# Plan de Implementación — Spotify Sync Manager GUI

## Prototipo interactivo

**`gui/SpotifySyncManager.html`** — ábrelo directo en el navegador (doble click). Muestra las 5 vistas completamente funcionales con datos mock del proyecto real.

---

## Stack recomendado

| Capa | Tecnología | Justificación |
|---|---|---|
| **Backend** | FastAPI (Python) | Envuelve los scripts existentes, expone WebSocket para logs en tiempo real |
| **Frontend** | React + Vite | El prototipo HTML ya valida el diseño; migración limpia |
| **IPC real-time** | WebSocket + subprocess | Para streaming de stdout de los scripts Python |
| **Empaquetado** | Tauri ó Electron | Opcional: convertir la web app en app de escritorio nativa |

> El proyecto ya tiene `kivy` en requirements pero para esta UI (tablas, terminal, modales) una web app supera a Kivy en capacidades y velocidad de desarrollo.

---

## Arquitectura

```
Spotify-sing-Android/
├── src/                    # Módulos Python existentes (sin cambios)
├── tools/                  # Scripts existentes (sin cambios)
├── gui/
│   ├── backend/
│   │   ├── main.py         # FastAPI app
│   │   ├── ws_runner.py    # WebSocket runner (subprocess → stream)
│   │   ├── routes/
│   │   │   ├── compare.py  # GET /api/compare
│   │   │   ├── queue.py    # GET/POST/PATCH /api/queue
│   │   │   ├── youtube.py  # GET /api/youtube/search
│   │   │   └── scripts.py  # POST /api/scripts/run
│   │   └── models.py       # Pydantic schemas
│   ├── frontend/
│   │   ├── src/
│   │   │   ├── views/      # CompareView, QueueView, MonitorView, SettingsView
│   │   │   ├── components/ # LangBadge, ScoreBadge, YtThumb...
│   │   │   └── App.tsx
│   │   └── package.json
│   └── SpotifySyncManager.html   # prototipo HTML interactivo
└── sync.py
```

---

## Fases de implementación

### Fase 1 — Validar diseño con el prototipo

- [ ] Abrir `gui/SpotifySyncManager.html` en el browser
- [ ] Navegar las 5 vistas, identificar ajustes de UX
- [ ] Confirmar flujo: Compare → agregar a Cola → buscar en YouTube → aprobar → Descargar

**Entregable:** diseño aprobado, lista de ajustes

---

### Fase 2 — Backend FastAPI (1-2 días)

```python
# Endpoints mínimos para arrancar
GET  /api/compare          # Correr smart_compare.py → JSON de tracks con match status
GET  /api/queue            # Leer cola actual (en memoria o JSON)
PATCH /api/queue/{id}      # Aprobar / rechazar item
GET  /api/youtube/search   # Buscar alternativa (youtube_client.py)
POST /api/scripts/run      # Ejecutar cualquier script de /tools/
WS   /ws/logs              # Stream de stdout en tiempo real
GET  /api/config           # Leer config.json
POST /api/config           # Escribir config.json
```

El `ws_runner.py` hace `subprocess.Popen` del script seleccionado y envía cada línea de `stdout/stderr` por WebSocket:

```python
@app.websocket("/ws/logs")
async def ws_logs(ws: WebSocket):
    await ws.accept()
    proc = await asyncio.create_subprocess_exec(
        "python", script_path,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
    )
    async for line in proc.stdout:
        await ws.send_text(line.decode())
```

---

### Fase 3 — Frontend React (2-3 días)

Migrar el prototipo HTML a Vite + React + TypeScript. La lógica del prototipo ya está validada, solo se conecta al backend real:

```ts
// hooks/useCompare.ts
const { data } = useSWR('/api/compare', fetcher);

// hooks/useWebSocket.ts — para el Monitor
const socket = new WebSocket('ws://localhost:8000/ws/logs');
socket.onmessage = (e) => setLogs(l => [...l, parseLine(e.data)]);
```

**Componentes clave a migrar del prototipo:**
- `CompareView` — tabla con datos reales de `smart_compare.py`
- `DownloadQueueView` — estado persistente via API
- `YouTubeSearchModal` — llamar a `youtube_client.py` via API
- `ProcessMonitorView` — WebSocket conectado al runner real
- `SettingsView` — leer/escribir `~/.spotifytoyoutube/config.json`

---

### Fase 4 — Integración real-time (1 día)

- Conectar el progress bar del Monitor a los logs reales (parsear `[X/Y]` del stdout)
- Auto-refrescar la vista Compare cuando un script termina
- Toast notifications cuando termina una descarga

---

### Fase 5 — Empaquetado opcional (½ día)

```bash
# Opción A: App de escritorio con Tauri (más liviana)
npm run tauri build

# Opción B: Solo servidor local (más simple)
python gui/backend/main.py  # abre browser automáticamente en localhost:8000
```

---

## Orden de implementación sugerido

```
Semana 1:
  Día 1: Revisar prototipo → ajustes de UX → instalar FastAPI
  Día 2: Endpoints /compare + /queue + /config
  Día 3: WebSocket runner + integrar generate_report.py
  Día 4: Frontend Vite setup + migrar CompareView
  Día 5: Migrar QueueView + YouTubeSearchModal

Semana 2:
  Día 1: Migrar MonitorView + WebSocket real
  Día 2: SettingsView + leer/escribir config real
  Día 3: Testing integration + edge cases
  Día 4: Pulir UX, loading states, error handling
  Día 5: Empaquetado + README
```

---

## Próximos pasos inmediatos

1. Abre el prototipo → `gui/SpotifySyncManager.html` (doble click en el explorador)
2. Ajusta UX antes de pasar al backend
3. Cuando apruebes el diseño: `pip install fastapi uvicorn` y arrancamos con `gui/backend/main.py`
