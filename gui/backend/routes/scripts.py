from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(tags=["scripts"])

TOOLS_DIR = Path(__file__).parent.parent.parent.parent / "tools"

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


@router.get("/scripts", response_model=list[ScriptInfo])
def list_scripts():
    return [
        ScriptInfo(name=s, path=str(TOOLS_DIR / s))
        for s in ALLOWED_SCRIPTS
        if (TOOLS_DIR / s).exists()
    ]
