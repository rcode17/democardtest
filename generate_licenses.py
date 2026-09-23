"""
Generador de licencias para CardChecker
Crea licencias en Firebase Realtime Database
"""
import json
import random
import string
import urllib.request
import urllib.error
from datetime import datetime, timedelta

FIREBASE_URL = "https://gentokendev-default-rtdb.firebaseio.com"


def generate_license_key() -> str:
    """Genera una clave tipo CCR-XXXX-XXXX-XXXX"""
    def random_block():
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    
    return f"CCR-{random_block()}-{random_block()}-{random_block()}"


def create_license(key: str, days_valid: int = 365) -> bool:
    """
    Crea una licencia en Firebase.
    
    Args:
        key: Clave de licencia (ej: CCR-0001-A1B2)
        days_valid: Días de validez desde hoy
    
    Returns:
        True si se creó exitosamente
    """
    expiry_date = (datetime.now() + timedelta(days=days_valid)).strftime("%Y-%m-%d")
    
    license_data = {
        "active": True,
        "expiry_date": expiry_date,
        "hardware_id": None  # Se asigna cuando el usuario activa
    }
    
    url = f"{FIREBASE_URL}/licenses/{key}.json"
    
    try:
        data = json.dumps(license_data).encode('utf-8')
        req = urllib.request.Request(
            url, 
            data=data, 
            headers={'Content-Type': 'application/json'},
            method='PUT'
        )
        urllib.request.urlopen(req, timeout=10)
        return True
    except Exception as e:
        print(f"❌ Error creando {key}: {e}")
        return False


def batch_create_licenses(count: int, days_valid: int = 365, prefix: str = None):
    """
    Crea múltiples licencias en lote.
    
    Args:
        count: Número de licencias a crear
        days_valid: Días de validez
        prefix: Prefijo personalizado (ej: "USER-01") o None para auto-generar
    """
    print(f"🔧 Generando {count} licencias válidas por {days_valid} días...\n")
    
    licenses = []
    
    for i in range(1, count + 1):
        if prefix:
            # Usar prefijo personalizado
            key = f"CCR-{prefix}-{i:04d}"
        else:
            # Generar clave aleatoria
            key = generate_license_key()
        
        print(f"[{i}/{count}] Creando {key}...", end=" ")
        
        if create_license(key, days_valid):
            print("✅")
            licenses.append(key)
        else:
            print("❌")
    
    print(f"\n✅ {len(licenses)} licencias creadas exitosamente\n")
    
    # Guardar en archivo para distribuir
    output_file = "licenses_generated.txt"
    with open(output_file, "w") as f:
        f.write(f"CardChecker - Licencias generadas\n")
        f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Válidas hasta: {(datetime.now() + timedelta(days=days_valid)).strftime('%Y-%m-%d')}\n")
        f.write("="*60 + "\n\n")
        
        for idx, lic in enumerate(licenses, 1):
            f.write(f"Usuario {idx:02d}: {lic}\n")
    
    print(f"📄 Licencias guardadas en: {output_file}")
    print(f"\n💡 Distribuye estos códigos a tus usuarios.")


if __name__ == "__main__":
    print("="*60)
    print("       GENERADOR DE LICENCIAS - CARDCHECKER")
    print("="*60 + "\n")
    
    # ── CONFIGURACIÓN ──
    NUM_LICENSES = 10        # Número de licencias a crear
    DAYS_VALID = 365         # Días de validez (1 año)
    CUSTOM_PREFIX = None     # None para aleatorio, o "2024" para CCR-2024-0001
    
    print(f"📊 Configuración:")
    print(f"   • Licencias: {NUM_LICENSES}")
    print(f"   • Validez: {DAYS_VALID} días")
    print(f"   • Prefijo: {'Aleatorio' if not CUSTOM_PREFIX else CUSTOM_PREFIX}\n")
    
    confirm = input("¿Continuar? (s/n): ").strip().lower()
    
    if confirm == 's':
        batch_create_licenses(NUM_LICENSES, DAYS_VALID, CUSTOM_PREFIX)
    else:
        print("❌ Operación cancelada")
