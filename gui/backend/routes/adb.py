import subprocess
from fastapi import APIRouter

router = APIRouter(tags=["adb"])


def _list_serials() -> list[str]:
    r = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=5)
    lines = r.stdout.strip().splitlines()
    return [l.split("\t")[0].strip() for l in lines[1:] if l.strip() and "\tdevice" in l]


def _get_prop(serial: str, prop: str) -> str:
    try:
        r = subprocess.run(
            ["adb", "-s", serial, "shell", "getprop", prop],
            capture_output=True, text=True, timeout=5,
        )
        return r.stdout.strip()
    except Exception:
        return ""


@router.get("/adb/status")
def adb_status():
    try:
        serials = _list_serials()
        if not serials:
            return {"connected": False, "device": None}
        serial = serials[0]
        model = _get_prop(serial, "ro.product.model") or serial
        brand = _get_prop(serial, "ro.product.brand")
        return {
            "connected": True,
            "device": {
                "serial": serial,
                "model": f"{brand} {model}".strip() if brand else model,
            },
        }
    except Exception:
        return {"connected": False, "device": None}


@router.get("/adb/scan")
def adb_scan():
    """Trigger adb connect discovery on TCP/IP (USB devices already show up via adb devices)."""
    try:
        subprocess.run(["adb", "start-server"], capture_output=True, timeout=8)
        return adb_status()
    except Exception:
        return {"connected": False, "device": None}
