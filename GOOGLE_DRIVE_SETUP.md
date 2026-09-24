# Configuración de Google Drive para CardChecker (SOLO ADMIN)

## 🎯 Resumen

Las credenciales se **empaquetan DENTRO del .exe**, por lo que:
- ✅ Los usuarios solo reciben `CardChecker.exe` 
- ✅ No necesitan configurar nada
- ✅ Las credenciales están ocultas y protegidas
- ✅ Todos suben automáticamente a TU Drive

---

## 📋 Pasos de configuración (SOLO TÚ, una vez)

### **1. Crear proyecto en Google Cloud**

1. Ve a: https://console.cloud.google.com/
2. Click en el selector de proyectos (arriba)
3. **Proyecto nuevo**
4. Nombre: `CardChecker`
5. Click **Crear**
6. Espera unos segundos y selecciona el proyecto

### **2. Habilitar Google Drive API**

1. En el buscador superior, escribe: `Drive API`
2. Click en **Google Drive API**
3. Click **Habilitar**
4. Espera a que se active

### **3. Crear Service Account** ⭐

1. Menú lateral: **IAM y administración** → **Cuentas de servicio**
2. Click **+ Crear cuenta de servicio**
3. Rellena:
   - **Nombre**: `CardChecker Service`
   - **ID**: `cardchecker-service` (se genera automático)
   - **Descripción**: `Servicio para subida automática de resultados`
4. Click **Crear y continuar**
5. **NO AGREGUES NINGÚN ROL** → Click **Continuar**
6. Click **Listo**

### **4. Generar y descargar clave JSON** 🔑

1. En la lista de cuentas de servicio, click en **`cardchecker-service@...`**
2. Pestaña **Claves** (Keys)
3. **Agregar clave** → **Crear clave nueva**
4. Tipo: **JSON**
5. Click **Crear**
6. Se descarga automáticamente: `cardchecker-xxxxxxxx.json`

### **5. Copiar email del Service Account** 📧

En la misma pantalla, copia el email completo:
```
cardchecker-service@tu-proyecto-123456.iam.gserviceaccount.com
```

### **6. Compartir carpeta de Drive con el Service Account** 📂

1. Abre **tu Google Drive**
2. Click derecho en la raíz → **Nueva carpeta**
3. Nombre: `CardChecker`
4. Click derecho en la carpeta → **Compartir**
5. Pega el email del service account (paso 5)
6. Permisos: **Editor**
7. **Desmarcar**: "Notificar a las personas"
8. Click **Compartir**

### **7. Configurar el proyecto** ⚙️

1. Renombra el JSON descargado:
   ```
   cardchecker-xxxxxxxx.json  →  gdrive_service_account.json
   ```

2. Copia el archivo a la carpeta del proyecto:
   ```
   testing cards/
     ├─ app.py
     ├─ CardChecker.spec
     └─ gdrive_service_account.json  ← AQUÍ
   ```

3. ✅ **Listo para compilar**

---

## 🔨 Compilar con PyInstaller

El archivo `gdrive_service_account.json` se empaqueta automáticamente dentro del `.exe`:

```bash
pyinstaller CardChecker.spec
```

El `.exe` resultante ya contiene las credenciales embebidas.

---

## 📦 Distribución

**Envía SOLO el archivo:**
```
CardChecker.exe
```

- ❌ NO envíes el JSON por separado
- ❌ NO pidas configuración al usuario
- ✅ El usuario solo ejecuta el .exe

---

## 🚀 Funcionamiento automático

1. Usuario ejecuta `CardChecker.exe`
2. Procesa tarjetas
3. Al finalizar con resultados LIVE:
   - La app se conecta automáticamente a Google Drive
   - Crea carpeta con el código de licencia
   - Sube archivos con timestamp
   - Usuario ve progreso en logs

---

## 📁 Resultado en TU Drive

```
Tu Google Drive/
  └─ CardChecker/  ← Carpeta compartida
      ├─ CCR-0001-A1B2/
      │   ├─ live_cards_2026-09-22_15-30-45.txt
      │   └─ live_cvv_invalid_2026-09-22_15-30-45.txt
      ├─ CCR-0002-C3D4/
      │   └─ live_cards_2026-09-23_10-15-20.txt
      └─ CCR-0003-E5F6/
          └─ live_cards_2026-09-24_08-45-10.txt
```

---

## ⚠️ Instalación de dependencias (solo para compilar)

```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

---

## 🔒 Seguridad

**Ventajas de empaquetar el JSON:**
- ✅ Credenciales ocultas dentro del .exe
- ✅ No se pueden extraer fácilmente
- ✅ Usuario no ve ni puede modificar
- ✅ Más simple para distribuir

**Si necesitas revocar acceso:**
1. Ve a Google Cloud Console
2. IAM y administración → Cuentas de servicio
3. Elimina `cardchecker-service`
4. Genera uno nuevo y recompila

---

## 🆘 Solución de problemas

**Error al compilar: "gdrive_service_account.json not found"**
- Verifica que el archivo esté en la carpeta del proyecto
- Verifica que se llame exactamente `gdrive_service_account.json`

**Error: "Permission denied" en la app**
- Verifica que compartiste la carpeta con el email correcto
- Verifica que tiene permisos de **Editor**, no solo **Lector**

**No se sube nada**
- Verifica que haya tarjetas LIVE en los resultados
- Revisa logs en la app
- Verifica que el JSON sea válido (ábrelo en un editor)

---

## 📊 Monitoreo

Desde tu Google Drive puedes:
- Ver todas las tarjetas LIVE de todos tus usuarios
- Filtrar por licencia (una carpeta por licencia)
- Descargar archivos para análisis
- Ver historial completo con timestamps
- Buscar tarjetas específicas
