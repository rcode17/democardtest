"""
Debug detallado — captura TODAS las URLs visitadas después de enviar el pago.
"""
import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

EMAIL    = "rickyzooo95@gmail.com"
PASSWORD = "1063171808"

TARJETA = {"number": "4833120197446991", "expiry_month": "02", "expiry_year": "2031", "cvv": "778"}

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        context = await browser.new_context()
        page    = await context.new_page()

        # Registrar TODAS las navegaciones
        url_history = []
        page.on("framenavigated", lambda frame: url_history.append(frame.url) if frame == page.main_frame else None)

        # Login
        await page.goto("https://ver.flixole.com/log-in", wait_until="networkidle")
        try:
            await page.click("text=Aceptar todo", timeout=5_000)
        except PlaywrightTimeout:
            pass
        await page.fill('input[type="email"]', EMAIL)
        await page.fill('input[type="password"]', PASSWORD)
        await page.click('button[type="submit"]')
        await page.wait_for_function("() => !window.location.href.includes('/log-in')", timeout=20_000)
        print(f"Login OK → {page.url}")

        # Checkout
        await page.goto("https://ver.flixole.com/checkout", wait_until="networkidle")
        m = page.locator('text=mensual').first
        if await m.count() > 0:
            await m.click(timeout=5_000)
        btn = page.locator('button:has-text("Continuar")').first
        await btn.wait_for(state="visible", timeout=10_000)
        await btn.click()
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2_000)
        print(f"Checkout: {page.url}")

        num_frame = page.frame_locator('iframe[title*="número de tarjeta"]')

        print(f"Rellenando número...")
        num_input = num_frame.locator('input[autocomplete="cc-number"], input[placeholder*="1234"]')
        await num_input.click()
        await num_input.type(TARJETA["number"], delay=50)
        await page.wait_for_timeout(500)

        print(f"Rellenando nombre del titular...")
        # El campo nombre de titular está FUERA de los iframes, en la página principal
        name_selectors = [
            'input[name="holderName"]',
            'input[placeholder*="ombre"]',
            'input[placeholder*="Titular"]',
            'input[autocomplete="cc-name"]:not([aria-hidden])',
            '.adyen-checkout__card__holderName input',
        ]
        name_filled = False
        for sel in name_selectors:
            el = page.locator(sel)
            if await el.count() > 0:
                await el.first.click()
                await el.first.type("Juan Perez", delay=50)
                print(f"  → Nombre rellenado con selector: {sel}")
                name_filled = True
                break
        if not name_filled:
            print("  → Campo nombre NO encontrado en página principal")
            # Listar todos los inputs visibles fuera de iframes
            inputs = await page.locator('input:visible').all()
            for inp in inputs:
                n = await inp.get_attribute("name") or ""
                p = await inp.get_attribute("placeholder") or ""
                a = await inp.get_attribute("autocomplete") or ""
                print(f"     input: name={n} placeholder={p} autocomplete={a}")
        await page.wait_for_timeout(500)

        print(f"Rellenando fecha...")
        exp_frame = page.frame_locator('iframe[title*="caducidad"]')
        exp_input = exp_frame.locator('input[placeholder="MM/AA"]')
        await exp_input.click()
        await exp_input.type(f"{TARJETA['expiry_month']}{TARJETA['expiry_year'][-2:]}", delay=50)
        await page.wait_for_timeout(500)

        print(f"Rellenando CVV...")
        cvc_frame = page.frame_locator('iframe[title*="seguridad"]')
        cvc_input = cvc_frame.locator('input[placeholder*="dígitos"]')
        await cvc_input.click()
        await cvc_input.type(TARJETA["cvv"], delay=50)
        await page.wait_for_timeout(1_500)

        await page.screenshot(path="debug_antes_pago.png")
        print("Captura antes del pago → debug_antes_pago.png")

        # Listar TODOS los botones visibles antes de enviar
        print("\n=== BOTONES VISIBLES EN EL FORMULARIO ===")
        buttons = await page.locator("button:visible").all()
        for i, btn_el in enumerate(buttons):
            txt  = (await btn_el.inner_text()).strip()
            cls  = await btn_el.get_attribute("class") or ""
            typ  = await btn_el.get_attribute("type") or ""
            print(f"  [{i}] type={typ} text='{txt}' class='{cls[:50]}'")
        print("==========================================\n")

        print("Enviando pago...")

        # Limpiar historial y enviar
        url_history.clear()
        # Verificar estado del botón antes de hacer clic
        pay_btn = page.locator('button.adyen-checkout__button--pay')
        disabled = await pay_btn.get_attribute("disabled")
        aria_disabled = await pay_btn.get_attribute("aria-disabled")
        btn_class = await pay_btn.get_attribute("class") or ""
        print(f"Botón pago → disabled={disabled} aria-disabled={aria_disabled}")
        print(f"Botón pago → class={btn_class}")

        print("Enviando pago con clic directo...")
        await pay_btn.click(force=True)

        # Esperar hasta 30 segundos capturando todas las URLs
        print("Esperando respuesta (30s)...")
        for i in range(30):
            await asyncio.sleep(1)
            current = page.url
            print(f"  t+{i+1:02d}s → {current}")
            await page.screenshot(path=f"debug_t{i+1:02d}.png")
            if "receipt" in current or "pago-exitoso" in current:
                print("✅ PÁGINA DE ÉXITO DETECTADA")
                break

        print(f"\nURLs visitadas: {url_history}")
        body = (await page.inner_text("body")).lower()
        print(f"\nTexto final (primeros 300 chars):\n{body[:300]}")

        await browser.close()

asyncio.run(main())
