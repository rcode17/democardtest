"""
Sistema de licencias — Firebase Realtime Database
Valida: license key + hardware ID + fecha de vencimiento + dispositivo único
"""
import hashlib
import json
import platform
import socket
import uuid
import urllib.request
import urllib.error
import logging
from datetime import datetime

# Silenciar logs de urllib
logging.getLogger("urllib3").setLevel(logging.CRITICAL)
logging.getLogger("urllib").setLevel(logging.CRITICAL)

FIREBASE_URL = "https://gentokendev-default-rtdb.firebaseio.com"


def get_hardware_id() -> str:
    """
    Genera un ID único del dispositivo combinando:
    - MAC address
    - Nombre del equipo
    - Plataforma del sistema
    Todo hasheado con SHA256 para no exponer datos sensibles.
    """
    try:
        mac     = hex(uuid.getnode())
        host    = socket.gethostname()
        system  = platform.system() + platform.release()
        raw     = f"{mac}-{host}-{system}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]
    except Exception:
        return hashlib.sha256(b"fallback-device").hexdigest()[:32]


def _firebase_get(path: str) -> dict | None:
    """Hace GET a Firebase y retorna el JSON o None si falla."""
    url = f"{FIREBASE_URL}/{path}.json"
    try:
        req  = urllib.request.Request(url, headers={"Accept": "application/json"})
        resp = urllib.request.urlopen(req, timeout=8)
        data = json.loads(resp.read().decode())
        return data
    except urllib.error.HTTPError as e:
        if e.code == 401 or e.code == 403:
            return {"_error": "unauthorized"}
        return None
    except Exception:
        return None


def _firebase_patch(path: str, data: dict) -> bool:
    """Hace PATCH a Firebase para actualizar campos específicos."""
    url     = f"{FIREBASE_URL}/{path}.json"
    payload = json.dumps(data).encode()
    try:
        req = urllib.request.Request(
            url, data=payload, method="PATCH",
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=8)
        return True
    except Exception:
        return False


def validate_license(key: str) -> tuple[bool, str]:
    """
    Valida la licencia contra Firebase.

    Retorna:
        (True, "OK")                         — licencia válida
        (False, "NO_INTERNET")               — sin conexión
        (False, "INVALID_KEY")               — clave no existe
        (False, "INACTIVE")                  — licencia desactivada
        (False, "EXPIRED:2026-01-01")        — vencida
        (False, "DEVICE_LOCKED:XXXX")        — bloqueada a otro dispositivo
    """
    # 1. Verificar conexión y obtener datos de la licencia
    data = _firebase_get(f"licenses/{key}")

    if data is None:
        return False, "NO_INTERNET"

    if data == "null" or (isinstance(data, dict) and "_error" in data):
        return False, "NO_INTERNET"

    if not isinstance(data, dict) or not data:
        return False, "INVALID_KEY"

    # 2. Verificar si está activa
    if not data.get("active", False):
        return False, "INACTIVE"

    # 3. Verificar fecha de vencimiento
    expiry_str = data.get("expiry_date", "")
    if expiry_str:
        try:
            expiry = datetime.strptime(expiry_str, "%Y-%m-%d")
            if datetime.now() > expiry:
                return False, f"EXPIRED:{expiry_str}"
        except ValueError:
            pass

    # 4. Verificar hardware ID (bloqueo por dispositivo)
    hw_id         = get_hardware_id()
    stored_hw_id  = data.get("hardware_id", "")

    if not stored_hw_id:
        # Primera activación — registrar este dispositivo
        ok = _firebase_patch(f"licenses/{key}", {"hardware_id": hw_id})
        if not ok:
            return False, "NO_INTERNET"
    elif stored_hw_id != hw_id:
        # Diferente dispositivo — acceso denegado
        return False, f"DEVICE_LOCKED:{stored_hw_id[:8]}..."

    return True, "OK"


def get_expiry_date(key: str) -> str | None:
    """Retorna la fecha de vencimiento de la licencia o None."""
    data = _firebase_get(f"licenses/{key}")
    if isinstance(data, dict):
        return data.get("expiry_date")
    return None


def error_message(reason: str) -> str:
    """Convierte el código de error a mensaje legible para el usuario."""
    if reason == "NO_INTERNET":
        return "Sin conexión a internet.\nSe requiere conexión para verificar la licencia."
    if reason == "INVALID_KEY":
        return "Clave de licencia inválida.\nVerifica tu clave e inténtalo de nuevo."
    if reason == "INACTIVE":
        return "Licencia desactivada.\nContacta al desarrollador."
    if reason.startswith("EXPIRED"):
        date = reason.split(":", 1)[1] if ":" in reason else ""
        return f"Licencia vencida el {date}.\nContacta al desarrollador para renovar."
    if reason.startswith("DEVICE_LOCKED"):
        return "Esta licencia ya está activada en otro dispositivo.\nContacta al desarrollador."
    return "Error de verificación de licencia.\nContacta al desarrollador."
