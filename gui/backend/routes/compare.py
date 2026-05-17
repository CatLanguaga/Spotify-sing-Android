import os
import re
import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException

_ROOT = Path(os.environ.get("SPOTIFY_SYNC_ROOT", Path(__file__).resolve().parent.parent.parent.parent))
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

router = APIRouter(tags=["compare"])

REPORT_PATH = _ROOT / "reports" / "informe_inteligente.txt"
_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

_MISSING_LINE = re.compile(r'^#(\d+)\.\s+')


def _parse_report(text: str) -> dict:
    """Parse informe_inteligente.txt into structured data."""
    start_offset = 0
    analyzed = 0
    matched = 0
    blacklisted = 0
    missing_indices: list[int] = []

    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("Offset inicial:"):
            try: start_offset = int(line.split(":", 1)[1].strip())
            except ValueError: pass
        elif line.startswith("Tracks analizados:"):
            try: analyzed = int(line.split(":", 1)[1].strip())
            except ValueError: pass
        elif line.startswith("Coincidencias encontradas:"):
            try: matched = int(line.split(":", 1)[1].strip())
            except ValueError: pass
        elif line.startswith("En blacklist"):
            try: blacklisted = int(line.split(":", 1)[1].strip())
            except ValueError: pass
        else:
            m = _MISSING_LINE.match(line)
            if m:
                missing_indices.append(int(m.group(1)))

    range_start = start_offset + 1
    range_end   = start_offset + analyzed if analyzed else range_start

    return {
        "missing_indices": missing_indices,
        "matched": matched,
        "blacklisted": blacklisted,
        "missing_count": len(missing_indices),
        "analyzed_range": {"start": range_start, "end": range_end},
    }


@router.get("/compare/report")
def read_compare_report():
    """
    Parse the existing informe_inteligente.txt and return per-index status.
    Does NOT run smart_compare.py — use the Monitor for that.
    Returns 404 if no report exists yet.
    """
    if not REPORT_PATH.exists():
        raise HTTPException(
            404,
            "No report found. Run smart_compare.py from the Monitor view first.",
        )
    try:
        text = REPORT_PATH.read_text(encoding="utf-8", errors="replace")
        return _parse_report(text)
    except Exception as e:
        raise HTTPException(500, str(e))
