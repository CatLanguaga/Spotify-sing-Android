import subprocess
from fastapi import APIRouter

router = APIRouter(tags=["adb"])


@router.get("/adb/status")
def adb_status():
    try:
        result = subprocess.run(
            ["adb", "devices"],
            capture_output=True, text=True, timeout=5,
        )
        lines = result.stdout.strip().splitlines()
        # First line is "List of devices attached"; rest are actual devices
        devices = [l for l in lines[1:] if l.strip() and "\tdevice" in l]
        return {"connected": len(devices) > 0}
    except Exception:
        return {"connected": False}
