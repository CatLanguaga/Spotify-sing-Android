import subprocess
import sys

from fastapi import APIRouter, Body

router = APIRouter(tags=["adb"])

_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


def _list_serials() -> list[str]:
    r = subprocess.run(
        ["adb", "devices"],
        capture_output=True, text=True, timeout=5,
        creationflags=_NO_WINDOW,
    )
    lines = r.stdout.strip().splitlines()
    return [l.split("\t")[0].strip() for l in lines[1:] if l.strip() and "\tdevice" in l]


def _get_prop(serial: str, prop: str) -> str:
    try:
        r = subprocess.run(
            ["adb", "-s", serial, "shell", "getprop", prop],
            capture_output=True, text=True, timeout=5,
            creationflags=_NO_WINDOW,
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
        subprocess.run(["adb", "start-server"], capture_output=True, timeout=8, creationflags=_NO_WINDOW)
        return adb_status()
    except Exception:
        return {"connected": False, "device": None}


@router.post("/adb/enable-wifi")
def adb_enable_wifi():
    """Run adb tcpip 5555 on USB-connected device. Must call before disconnecting USB."""
    try:
        r = subprocess.run(
            ["adb", "tcpip", "5555"],
            capture_output=True, text=True, timeout=10,
            creationflags=_NO_WINDOW,
        )
        ok = r.returncode == 0 and "restarting" in r.stdout.lower()
        return {"ok": ok, "message": r.stdout.strip() or r.stderr.strip()}
    except Exception as e:
        return {"ok": False, "message": str(e)}


@router.get("/adb/device-ip")
def adb_device_ip():
    """Get IP of currently USB-connected device from wlan0."""
    try:
        r = subprocess.run(
            ["adb", "shell", "ip", "route"],
            capture_output=True, text=True, timeout=5,
            creationflags=_NO_WINDOW,
        )
        for line in r.stdout.splitlines():
            parts = line.split()
            if "src" in parts:
                idx = parts.index("src")
                if idx + 1 < len(parts):
                    return {"ip": parts[idx + 1]}
        return {"ip": None}
    except Exception:
        return {"ip": None}


@router.post("/adb/connect-wifi")
def adb_connect_wifi(ip: str = Body(..., embed=True)):
    """Connect to device over WiFi TCP/IP. Device must have had enable-wifi called first."""
    try:
        r = subprocess.run(
            ["adb", "connect", f"{ip}:5555"],
            capture_output=True, text=True, timeout=10,
            creationflags=_NO_WINDOW,
        )
        connected = "connected" in r.stdout.lower()
        return {"ok": connected, "message": r.stdout.strip()}
    except Exception as e:
        return {"ok": False, "message": str(e)}
