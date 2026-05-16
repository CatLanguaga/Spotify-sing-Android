"""
Punto de entrada de escritorio — arranca FastAPI en un thread y abre
una ventana nativa con pywebview apuntando a http://localhost:8000.

Uso (desarrollo):
    python gui/app.py

Uso (exe):
    Spotify Sync Manager.exe   (generado con build.ps1)

Requisitos:
    pip install pywebview
    (el dist/ de React debe estar construido: cd gui/frontend && npm run build)
"""

import os
import socket
import sys
import threading
import time
from pathlib import Path

# ── Resolver la raíz del proyecto ─────────────────────────────────────────
# PyInstaller congela el app en una carpeta; sys._MEIPASS apunta a ella.
# En modo script, la raíz es dos niveles arriba de este archivo.
if getattr(sys, "frozen", False):
    ROOT = Path(sys._MEIPASS)           # type: ignore[attr-defined]
else:
    ROOT = Path(__file__).resolve().parent.parent

# Exportar la raíz para que el backend y las rutas la usen.
os.environ["SPOTIFY_SYNC_ROOT"]  = str(ROOT)
os.environ["SPOTIFY_SYNC_TAURI"] = "1"   # evita que el backend abra el browser

# Añadir la raíz al path para que los imports de src/ funcionen.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ── Imports que dependen de que ROOT esté en sys.path ─────────────────────
import uvicorn
import webview  # noqa: E402  (orden intencional)


def _wait_for_port(port: int, timeout: float = 20.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.5).close()
            return True
        except OSError:
            time.sleep(0.2)
    return False


def _run_server() -> None:
    # Importar el app aquí (después de que ROOT esté en sys.path).
    from gui.backend.main import app as fastapi_app
    uvicorn.run(fastapi_app, host="127.0.0.1", port=8000, log_level="warning")


def main() -> None:
    dist = ROOT / "gui" / "frontend" / "dist"
    if not dist.exists():
        print(
            "[app] AVISO: gui/frontend/dist/ no existe.\n"
            "       Construí el frontend primero:\n"
            "         cd gui/frontend && npm run build\n"
            "       Luego volvé a correr: python gui/app.py"
        )
        sys.exit(1)

    server_thread = threading.Thread(target=_run_server, daemon=True)
    server_thread.start()

    print("[app] Esperando backend...", flush=True)
    if not _wait_for_port(8000):
        print("[app] ERROR: el backend no respondió en 20 segundos.")
        sys.exit(1)

    print("[app] Listo — abriendo ventana.", flush=True)

    webview.create_window(
        title="Spotify Sync Manager",
        url="http://localhost:8000",
        width=1280,
        height=820,
        min_size=(960, 600),
        text_select=False,
    )
    webview.start(debug=False)


if __name__ == "__main__":
    main()
