import os
import subprocess
import sys
from pathlib import Path

_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(tags=["scripts"])

_ROOT = Path(os.environ.get("SPOTIFY_SYNC_ROOT", Path(__file__).parent.parent.parent.parent))
TOOLS_DIR = _ROOT / "tools"

ALLOWED_SCRIPTS = {
    "smart_compare.py",
    "generate_report.py",
    "enrich_metadata.py",
    "download_missing.py",
    "dry_run.py",
}


class ScriptInfo(BaseModel):
    name: str
    path: str


class ScriptRun(BaseModel):
    script: str
    args: list[str] = []


@router.get("/scripts", response_model=list[ScriptInfo])
def list_scripts():
    return [
        ScriptInfo(name=s, path=str(TOOLS_DIR / s))
        for s in ALLOWED_SCRIPTS
        if (TOOLS_DIR / s).exists()
    ]


@router.post("/scripts/run")
def run_script(body: ScriptRun):
    """Run an allowed script synchronously and return its exit code and tail of output."""
    if body.script not in ALLOWED_SCRIPTS:
        raise HTTPException(400, f'Script "{body.script}" not allowed')

    script_path = TOOLS_DIR / body.script
    if not script_path.exists():
        raise HTTPException(404, f'Script "{body.script}" not found')

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)] + body.args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
            cwd=str(_ROOT),
            creationflags=_NO_WINDOW,
        )
        return {
            "returncode": result.returncode,
            "stdout": result.stdout[-3000:],
            "stderr": result.stderr[-500:] if result.stderr else "",
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(504, f'Script "{body.script}" timed out (>600s)')
    except Exception as e:
        raise HTTPException(500, str(e))
