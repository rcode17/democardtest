# FlixOlé Card Checker

Automatiza el proceso de suscripción en FlixOlé con múltiples tarjetas propias.

## Instalación

```bash
pip install playwright
playwright install chromium
```

## Configuración

### 1. Edita `cards.csv` con tus tarjetas

```csv
number,expiry_month,expiry_year,cvv,name
4111111111111111,12,2027,123,Tu Nombre
5500005555555559,06,2026,456,Tu Nombre
```

| Campo          | Descripción                     |
|----------------|---------------------------------|
| `number`       | Número completo de la tarjeta   |
| `expiry_month` | Mes de vencimiento (01-12)      |
| `expiry_year`  | Año de vencimiento (ej: 2027)   |
| `cvv`          | Código CVV/CVC                  |
| `name`         | Nombre del titular              |

### 2. Edita `flixole_checker.py`

Cambia estas dos líneas con tus credenciales de FlixOlé:

```python
EMAIL    = "tu@email.com"
PASSWORD = "tu_contraseña"
```

## Ejecución

```bash
python flixole_checker.py
```

## Salida

- **Consola**: reporte en tiempo real con ✅ / ❌ por tarjeta
- **`resultados.json`**: archivo con todos los detalles
- **`screenshot_XXXX.png`**: captura del estado final de cada tarjeta (para depuración)

## Ejemplo de reporte

```
============================================================
  REPORTE DE TARJETAS
============================================================

✅ APROBADAS (1):
   ****1111  12/2027  Juan Perez
       → Pago aprobado

❌ FALLIDAS (2):
   ****5559  06/2026  Juan Perez
       → Tarjeta denegada
   ****4242  09/2028  Juan Perez
       → Timeout esperando respuesta del pago

============================================================
  Total: 3 | OK: 1 | FAIL: 2
============================================================
```

## Notas

- El script abre el navegador visible (`HEADLESS = False`) para que puedas ver qué hace.  
  Cámbialo a `True` para ejecutar en segundo plano.
- Cada tarjeta usa su propio contexto de navegador (sesión limpia).
- Si FlixOlé usa Stripe o Adyen dentro de un iframe, el script lo detecta automáticamente.
