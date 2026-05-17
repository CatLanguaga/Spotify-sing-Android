import asyncio
import os
import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["websocket"])

_ROOT = Path(os.environ.get("SPOTIFY_SYNC_ROOT", Path(__file__).resolve().parent.parent.parent))
TOOLS_DIR = _ROOT / "tools"
_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

ALLOWED_SCRIPTS = {
    "smart_compare.py",
    "generate_report.py",
    "enrich_metadata.py",
    "download_missing.py",
    "dry_run.py",
}


@router.websocket("/ws/logs")
async def ws_logs(websocket: WebSocket, script: str = "smart_compare.py"):
    await websocket.accept()

    if script not in ALLOWED_SCRIPTS:
        await websocket.send_text(f'[ERROR] Script "{script}" not allowed\n')
        await websocket.close()
        return

    script_path = TOOLS_DIR / script
    if not script_path.exists():
        await websocket.send_text(f'[ERROR] Script "{script}" not found\n')
        await websocket.close()
        return

    await websocket.send_text(f'[INFO] Starting {script}...\n')

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            str(script_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(_ROOT),
            creationflags=_NO_WINDOW,
        )

        async for line in proc.stdout:
            try:
                await websocket.send_text(line.decode(errors="replace"))
            except WebSocketDisconnect:
                proc.kill()
                return

        await proc.wait()
        code = proc.returncode
        status = "INFO" if code == 0 else "ERROR"
        await websocket.send_text(f'[{status}] Process exited with code {code}\n')

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_text(f'[ERROR] {e}\n')
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
