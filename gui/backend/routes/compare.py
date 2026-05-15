import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.config import ConfigManager

router = APIRouter(tags=["compare"])
_mgr = ConfigManager()

SMART_COMPARE = Path(__file__).parent.parent.parent.parent / "tools" / "smart_compare.py"


@router.get("/compare")
def run_compare():
    """Run smart_compare.py and return parsed JSON results."""
    cfg = _mgr.load_config()
    if not cfg:
        raise HTTPException(400, "Config not set. Call POST /api/config first.")

    try:
        result = subprocess.run(
            [sys.executable, str(SMART_COMPARE)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            raise HTTPException(500, result.stderr or "smart_compare.py failed")

        lines = result.stdout.splitlines()
        tracks = []
        for line in lines:
            if line.startswith("{"):
                import json
                try:
                    tracks.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

        return {"tracks": tracks, "raw": result.stdout if not tracks else None}

    except subprocess.TimeoutExpired:
        raise HTTPException(504, "smart_compare.py timed out (>120s)")
    except Exception as e:
        raise HTTPException(500, str(e))
