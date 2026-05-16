"""
Punto de entrada de escritorio — arranca FastAPI en un thread y abre
una ventana nativa con pywebview apuntando a http://localhost:8000.

Uso:
    python gui/app.py

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

# Signal to main.py that no debe abrir el browser
os.environ["SPOTIFY_SYNC_TAURI"] = "1"

# Asegurar que los imports de src/ funcionen
sys.path.insert(0, str(Path(__file__).parent.parent))

import uvicorn
import webview


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
    uvicorn.run(
        "gui.backend.main:app",
        host="127.0.0.1",
        port=8000,
        log_level="warning",
        # reload=False para que no spawne procesos extra
    )


def main() -> None:
    dist = Path(__file__).parent / "frontend" / "dist"
    if not dist.exists():
        print(
            "[app] AVISO: gui/frontend/dist/ no existe.\n"
            "       Construí el frontend primero:\n"
            "         cd gui/frontend && npm run build\n"
            "       Luego volvé a correr: python gui/app.py"
        )
        sys.exit(1)

    # Arrancar el backend en background
    server_thread = threading.Thread(target=_run_server, daemon=True)
    server_thread.start()

    print("[app] Esperando que el backend esté listo...", flush=True)
    if not _wait_for_port(8000):
        print("[app] ERROR: el backend no respondió en 20 segundos.")
        sys.exit(1)

    print("[app] Backend listo — abriendo ventana.", flush=True)

    window = webview.create_window(
        title="Spotify Sync Manager",
        url="http://localhost:8000",
        width=1280,
        height=820,
        min_size=(960, 600),
        text_select=False,
    )

    # Al cerrar la ventana el thread del servidor (daemon=True) se mata solo.
    webview.start(debug=False)


if __name__ == "__main__":
    main()
