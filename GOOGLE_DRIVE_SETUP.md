# Configuración de Google Drive para CardChecker (OAuth - Gmail personal)

## 🎯 Resumen

Usamos OAuth con token empaquetado para que todos los usuarios suban a TU Gmail personal sin necesidad de autenticar.

---

## 📋 Pasos de configuración (SOLO TÚ, una vez)

### **1. Crear proyecto en Google Cloud** (si no lo hiciste)

1. Ve a: https://console.cloud.google.com/
2. Selecciona tu proyecto existente: `My Project 83724`

### **2. Habilitar Google Drive API** (ya está hecho)

✅ Ya hiciste este paso

### **3. Configurar pantalla de consentimiento OAuth**

1. Ve a: https://console.cloud.google.com/apis/credentials/consent
2. Si dice "Internal", NO problem. Si dice "External", continúa:
3. Click **"EDITAR APP"** o **"Configurar pantalla de consentimiento"**
4. Tipo de usuario: **Externo**
5. Información de la app:
   - Nombre: `CardChecker`
   - Email de asistencia: tu email
   - Logo: (opcional)
6. Ámbitos: Click **"AGREGAR O QUITAR ÁMBITOS"**
   - Busca: `drive.file`
   - Marca: `.../auth/drive.file` (Ver y administrar archivos de Drive creados por esta app)
   - **Guardar y continuar**
7. Usuarios de prueba: **Agregar tu email** (`rjayala70@gmail.com`)
8. **Guardar** y **Volver al panel**

### **4. Crear credenciales OAuth**

1. Ve a: https://console.cloud.google.com/apis/credentials
2. **+ Crear credenciales** → **ID de cliente de OAuth**
3. Tipo de aplicación: **Aplicación de escritorio**
4. Nombre: `CardChecker Desktop`
5. **Crear**
6. **Descargar JSON** (ícono de descarga ⬇)
7. Renombra el archivo a: `gdrive_oauth_credentials.json`
8. Copia el archivo a la carpeta del proyecto:
   ```
   testing cards/
     ├─ app.py
     ├─ generate_gdrive_token.py
     └─ gdrive_oauth_credentials.json  ← AQUÍ
   ```

### **5. Generar token de autenticación**

Ejecuta el script generador:

```bash
python generate_gdrive_token.py
```

Esto hará:
1. Abrirá tu navegador
2. Te pedirá iniciar sesión con tu Gmail
3. Te pedirá autorizar la app
4. Generará `gdrive_token.pickle`

**IMPORTANTE:** Este token tiene tu autorización y se empaquetará en el .exe

### **6. Verificar archivos generados**

Debes tener:
```
testing cards/
  ├─ gdrive_oauth_credentials.json  (credenciales OAuth)
  ├─ gdrive_token.pickle             (token con tu autorización)
  └─ CardChecker.spec               (configuración build)
```

---

## 🔨 Compilar con PyInstaller

El `CardChecker.spec` se actualizará para incluir el token:

```python
datas=[
    ('icon.ico', '.'),
    ('logo.png', '.'),
    ('gdrive_token.pickle', '.'),  # Token empaquetado
    ...
],
```

Luego compila:
```bash
pyinstaller CardChecker.spec
```

---

## 📦 Distribución

**Envía SOLO:**
```
CardChecker.exe
```

- El token está empaquetado dentro
- Usuario NO necesita autenticar
- Todo sube automáticamente a TU Drive

---

## 🚀 Funcionamiento

1. Usuario ejecuta `CardChecker.exe`
2. Procesa tarjetas
3. Al finalizar con LIVE:
   - La app usa el token empaquetado
   - Se conecta a TU Google Drive
   - Crea carpeta con código de licencia
   - Sube archivos

4. Tú ves todo en:
   ```
   https://drive.google.com/drive/folders/1EbMdBSehgXkTtjd3dXEqWHYitgOxumwj
   ```

---

## 🔒 Seguridad

**Token empaquetado:**
- ✅ Tu autorización dentro del .exe
- ✅ Usuario no ve el token
- ✅ Todos suben a TU Drive

**Revocar acceso:**
1. Ve a: https://myaccount.google.com/permissions
2. Busca "CardChecker"
3. Click **"Quitar acceso"**
4. Genera nuevo token y recompila

---

## 🆘 Solución de problemas

**Error: "gdrive_oauth_credentials.json not found"**
- Descarga las credenciales OAuth desde Google Cloud Console
- Asegúrate de que sea tipo "Aplicación de escritorio"

**Error al generar token: "redirect_uri_mismatch"**
- Verifica que el tipo sea "Aplicación de escritorio"
- NO uses "Aplicación web"

**Token expirado**
- Los tokens de OAuth no expiran si tienen refresh_token
- Si expira, regenera con `generate_gdrive_token.py`

---

## 📊 Ventajas de este método

✅ Funciona con Gmail personal (no necesitas Workspace)  
✅ Token empaquetado = sin configuración para usuarios  
✅ Todos suben a TU Drive automáticamente  
✅ Puedes revocar acceso cuando quieras  
✅ Simple y seguro
