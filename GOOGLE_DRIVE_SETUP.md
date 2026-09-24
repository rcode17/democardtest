# Configuración de Google Drive para CardChecker

Esta guía explica cómo habilitar la subida automática de resultados LIVE a Google Drive.

## ⚠️ Requisitos

1. Instalar PyDrive2:
```bash
pip install PyDrive2
```

2. Tener una cuenta de Google (Gmail)

## 📋 Configuración (una sola vez)

### 1. Crear proyecto en Google Cloud Console

1. Ve a: https://console.cloud.google.com/
2. Crea un nuevo proyecto (ej: "CardChecker")
3. Selecciona el proyecto

### 2. Habilitar Google Drive API

1. En el menú lateral: **APIs y servicios** → **Biblioteca**
2. Busca "Google Drive API"
3. Click en **Habilitar**

### 3. Crear credenciales OAuth 2.0

1. **APIs y servicios** → **Credenciales**
2. Click **+ Crear credenciales** → **ID de cliente de OAuth**
3. Si pide configurar pantalla de consentimiento:
   - Tipo: **Externo**
   - Nombre de la aplicación: `CardChecker`
   - Correo de asistencia: tu email
   - Ámbitos: no agregar nada
   - Usuarios de prueba: **agregar tu email**
   - Guardar

4. Volver a **Credenciales** → **+ Crear credenciales** → **ID de cliente de OAuth**
   - Tipo de aplicación: **Aplicación de escritorio**
   - Nombre: `CardChecker Desktop`
   - Click **Crear**

5. **Descargar el JSON** (icono de descarga)
   - Te descargará algo como `client_secret_XXXXX.json`

### 4. Configurar CardChecker

1. Abre el archivo `settings.yaml` que está junto a `app.py`

2. Abre el JSON que descargaste y copia los valores:

```yaml
client_config_backend: settings
client_config:
  client_id: "TU_CLIENT_ID_AQUI.apps.googleusercontent.com"
  client_secret: "TU_CLIENT_SECRET_AQUI"

save_credentials: True
save_credentials_backend: file
save_credentials_file: .gdrive_credentials.json

get_refresh_token: True

oauth_scope:
  - https://www.googleapis.com/auth/drive.file
  - https://www.googleapis.com/auth/drive.install
```

3. Guarda el archivo

## 🚀 Primera ejecución

1. Ejecuta `CardChecker.exe`
2. Procesa algunas tarjetas
3. Al finalizar, si hay resultados LIVE:
   - Se abrirá tu navegador pidiendo autorización
   - Inicia sesión con tu cuenta de Google
   - Acepta los permisos
   - La ventana se cerrará automáticamente

4. Los archivos se subirán a:
```
Google Drive/
  └─ CardChecker/
      └─ CCR-XXXX-XXXX/
          ├─ live_cards_2026-09-22_15-30-45.txt
          └─ live_cvv_invalid_2026-09-22_15-30-45.txt
```

## 📁 Estructura de carpetas

Cada licencia tiene su propia carpeta:

```
CardChecker/
  ├─ CCR-0001-A1B2/
  │   ├─ live_cards_2026-09-22_15-30-45.txt
  │   └─ live_cvv_invalid_2026-09-22_15-30-45.txt
  │
  ├─ CCR-0002-C3D4/
  │   ├─ live_cards_2026-09-23_10-15-20.txt
  │   └─ live_cvv_invalid_2026-09-23_10-15-20.txt
  │
  └─ CCR-0003-E5F6/
      └─ live_cards_2026-09-24_08-45-10.txt
```

## 🔧 Desactivar subida automática

Si no quieres usar Google Drive:
- Simplemente NO instales PyDrive2
- La app funcionará normal pero sin subir a Drive

## ⚠️ Notas importantes

- Las credenciales se guardan en: `C:\Users\TuUsuario\.cardchecker_gdrive_credentials.txt`
- Solo necesitas autenticar **una vez por dispositivo**
- Los archivos se suben **automáticamente** al finalizar cada procesamiento
- Solo se suben tarjetas **LIVE** (OK y CVV inválido), no las rechazadas

## 🆘 Solución de problemas

**Error: "PyDrive2 not found"**
- Instala: `pip install PyDrive2`

**Error: "Authentication failed"**
- Verifica que `settings.yaml` tenga los valores correctos
- Borra `.gdrive_credentials.json` y vuelve a autenticar

**No se sube nada**
- Verifica que haya tarjetas LIVE en los resultados
- Revisa los logs en la app para ver mensajes de error
