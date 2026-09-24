"""
Gestión del periodo de prueba — 5 días desde primer uso.

Protecciones:
  1. Hora real obtenida de NTP (pool.ntp.org), con fallback a WorldTimeAPI
  2. Si el reloj del sistema está adelantado más de 1 día → bloqueo
  3. Fecha de instalación guardada ofuscada en el registro de Windows
  4. Sin internet → bloqueo
"""

import winreg
import ntplib
import base64
import hashlib
import requests
from datetime import datetime, timezone, timedelta

# ── Configuración ─────────────────────────────────────────────────────────────
REGISTRY_KEY   = r"SOFTWARE\CardCheckerR"
REGISTRY_VALUE = "cfg"
TRIAL_DAYS     = 5
NTP_SERVER     = "pool.ntp.org"
WORLDTIME_URL  = "http://worldtimeapi.org/api/timezone/Etc/UTC"
MAX_CLOCK_SKEW = 86_400   # 1 día en segundos — adelanto máximo tolerado del reloj local

# Clave de ofuscación derivada del nombre de la app
_KEY = hashlib.md5(b"CardCheckerR_2026").digest()


# ── Ofuscación ────────────────────────────────────────────────────────────────

def _xor(data: bytes) -> bytes:
    return bytes(b ^ _KEY[i % len(_KEY)] for i, b in enumerate(data))

def _encode(dt: datetime) -> str:
    return base64.b64encode(_xor(dt.isoformat().encode())).decode()

def _decode(s: str) -> datetime:
    return datetime.fromisoformat(_xor(base64.b64decode(s.encode())).decode())


# ── Obtener hora real ─────────────────────────────────────────────────────────

def _get_time_ntp() -> datetime | None:
    """Intenta obtener la hora desde el servidor NTP."""
    try:
        client = ntplib.NTPClient()
        resp   = client.request(NTP_SERVER, version=3, timeout=5)
        return datetime.fromtimestamp(resp.tx_time, tz=timezone.utc).replace(tzinfo=None)
    except Exception:
        return None


def _get_time_worldtime() -> datetime | None:
    """Fallback: obtiene la hora desde WorldTimeAPI."""
    try:
        resp = requests.get(WORLDTIME_URL, timeout=6)
        resp.raise_for_status()
        data = resp.json()
        # El campo puede ser "datetime" o "utc_datetime"
        raw  = data.get("utc_datetime") or data.get("datetime", "")
        # Normalizar — quitar offset si viene (+00:00)
        raw  = raw[:26].replace("Z", "")
        return datetime.fromisoformat(raw)
    except Exception:
        return None


def _get_real_time() -> datetime | None:
    """
    Intenta NTP primero, luego WorldTimeAPI.
    Retorna None si ambos fallan (sin internet o bloqueados).
    """
    t = _get_time_ntp()
    if t:
        return t
    return _get_time_worldtime()


# ── Registro ──────────────────────────────────────────────────────────────────

def _get_install_date() -> datetime | None:
    try:
        key    = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY)
        value, _ = winreg.QueryValueEx(key, REGISTRY_VALUE)
        winreg.CloseKey(key)
        return _decode(value)
    except Exception:
        return None


def _set_install_date(dt: datetime) -> None:
    try:
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY)
        winreg.SetValueEx(key, REGISTRY_VALUE, 0, winreg.REG_SZ, _encode(dt))
        winreg.CloseKey(key)
    except Exception:
        pass


# ── Check principal ───────────────────────────────────────────────────────────

def check_trial() -> tuple[bool, str]:
    """
    Verifica si el trial está activo.
    Retorna (activo: bool, motivo: str).

    motivos posibles:
      "ok"              → trial activo
      "no_internet"     → no se pudo contactar NTP ni WorldTimeAPI
      "clock_tampered"  → reloj del sistema manipulado
      "expired"         → periodo de 5 días expirado
    """
    # 1. Obtener hora real
    real_now = _get_real_time()
    if real_now is None:
        # Sin internet — permitir el uso pero no registrar fecha nueva
        # (si ya hay fecha registrada, continuar; si no, bloquear)
        install_date = _get_install_date()
        if install_date is None:
            return False, "no_internet"
        # Hay fecha registrada — verificar con el reloj local como fallback
        real_now = datetime.now()

    # 2. Detectar manipulación del reloj local
    local_now = datetime.now()
    skew = (local_now - real_now).total_seconds()
    if skew > MAX_CLOCK_SKEW:
        return False, "clock_tampered"

    # 3. Registrar/leer fecha de instalación
    install_date = _get_install_date()
    if install_date is None:
        _set_install_date(real_now)
        install_date = real_now

    # 4. Verificar expiración usando la hora real del servidor
    expiry = install_date + timedelta(days=TRIAL_DAYS)
    if real_now > expiry:
        return False, "expired"

    return True, "ok"
