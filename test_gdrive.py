"""Test rápido de subida a Google Drive con OAuth"""
from gdrive_uploader import GDriveUploader

# ID de tu carpeta compartida
DRIVE_FOLDER_ID = "1EbMdBSehgXkTtjd3dXEqWHYitgOxumwj"

# Datos de prueba
test_license = "CCR-TEST-0001"
test_cards = [
    {
        "number": "4532123456789012",
        "expiry_month": "12",
        "expiry_year": "2027",
        "cvv": "123"
    },
    {
        "number": "5412345678901234",
        "expiry_month": "06",
        "expiry_year": "2028",
        "cvv": "456"
    }
]

print("🧪 Probando subida a Google Drive con OAuth...")
print(f"📁 Carpeta compartida: {DRIVE_FOLDER_ID}")
print(f"🔑 Licencia de prueba: {test_license}")
print()

# Crear uploader
uploader = GDriveUploader(test_license, DRIVE_FOLDER_ID)

# Autenticar con token OAuth
print("🔐 Autenticando con token OAuth...")
if not uploader.authenticate("", "gdrive_token.pickle"):
    print("❌ Error en autenticación")
    exit(1)
print("✅ Autenticación exitosa")

# Crear carpetas
print("📂 Creando estructura de carpetas...")
if not uploader.setup_folders():
    print("❌ Error creando carpetas")
    exit(1)
print("✅ Carpetas creadas")

# Subir archivos de prueba
print("☁️ Subiendo archivos de prueba...")
if uploader.upload_results(test_cards, []):
    print("✅ Subida exitosa!")
    print()
    print(f"🎉 Revisa tu Drive en:")
    print(f"   https://drive.google.com/drive/folders/{DRIVE_FOLDER_ID}")
    print(f"   Busca la carpeta: {test_license}")
else:
    print("❌ Error subiendo archivos")
    exit(1)
