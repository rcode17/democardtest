"""
Genera token de OAuth para Google Drive (SOLO EJECUTAR UNA VEZ - ADMIN)
Este script abre el navegador para que autorices con tu cuenta de Google
"""
import pickle
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/drive.file']

print("="*60)
print("  GENERADOR DE TOKEN GOOGLE DRIVE - CardChecker")
print("="*60)
print()
print("Este script generará un token de autenticación para Google Drive")
print("que se empaquetará en el .exe")
print()

# Buscar archivo de credenciales OAuth
creds_file = Path("gdrive_oauth_credentials.json")

if not creds_file.exists():
    print("❌ Error: No se encontró gdrive_oauth_credentials.json")
    print()
    print("Pasos para obtenerlo:")
    print("1. Ve a: https://console.cloud.google.com/apis/credentials")
    print("2. + Crear credenciales → ID de cliente de OAuth")
    print("3. Tipo: Aplicación de escritorio")
    print("4. Descarga el JSON y renómbralo a: gdrive_oauth_credentials.json")
    exit(1)

print(f"✅ Archivo de credenciales encontrado")
print()

creds = None
token_file = Path("gdrive_token.pickle")

if token_file.exists():
    print("⚠ Ya existe un token. ¿Deseas generar uno nuevo? (s/n): ", end="")
    if input().strip().lower() != 's':
        print("Operación cancelada")
        exit(0)

print("🔐 Iniciando autenticación...")
print("Se abrirá tu navegador para autorizar la app")
print()

flow = InstalledAppFlow.from_client_secrets_file(str(creds_file), SCOPES)
creds = flow.run_local_server(port=0)

# Guardar token
with open(token_file, 'wb') as token:
    pickle.dump(creds, token)

print()
print("="*60)
print("✅ TOKEN GENERADO EXITOSAMENTE")
print("="*60)
print()
print(f"📁 Archivo creado: {token_file}")
print()
print("Próximos pasos:")
print("1. Este token se empaquetará automáticamente en el .exe")
print("2. Todos los usuarios subirán a TU Google Drive")
print("3. No necesitas hacer nada más")
print()
print("IMPORTANTE: Guarda este token de forma segura")
print("Si lo pierdes, deberás generar uno nuevo")
