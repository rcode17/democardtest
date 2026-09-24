"""
Prueba: cambiar método de pago en cuenta con suscripción activa.
Explora si FlixOlé permite agregar/cambiar tarjeta y qué respuesta da Adyen.
"""
import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

EMAIL    = "rickyzooo20@gmail.com"
PASSWORD = "1063171808"

# Tarjeta a probar
TARJETA = {"number": "4833120197446991", "expiry_month": "02", "expiry_year": "2031", "cvv": "778"}

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        page    = await browser.new_page()

        # Interceptar todas las respuestas de red
        async def on_response(response):
            url = response.url
            if any(k in url for k in ["adyen", "payments", "checkout", "flixole"]):
                try:
                    data = await response.json()
                    print(f"\n🌐 [{response.status}] {url[:80]}")
                    print(f"   {data}")
                except Exception:
                    pass

        page.on("response", on_response)

        # Login
        await page.goto("https://ver.flixole.com/log-in", wait_until="networkidle")
        try:
            await page.click("text=Aceptar todo", timeout=5_000)
        except PlaywrightTimeout:
            pass
        await page.fill('input[type="email"]', EMAIL)
        await page.fill('input[type="password"]', PASSWORD)
        await page.click('button[type="submit"]')
        await page.wait_for_function("() => !window.location.href.includes('/log-in')", timeout=15_000)
        print(f"Login OK → {page.url}")

        # Explorar sección de información de pago
        print("\n--- Explorando sección de pago ---")
        for url in [
            "https://ver.flixole.com/settings/billing",
            "https://ver.flixole.com/settings/payment",
            "https://ver.flixole.com/settings/payment-info",
        ]:
            await page.goto(url, wait_until="networkidle")
            body = await page.inner_text("body")
            buttons = await page.locator("button:visible").all_text_contents()
            print(f"\n>> {url} → {page.url}")
            print(f"   Botones: {[b.strip() for b in buttons if b.strip()]}")
            print(f"   Texto: {body[:300]}")
            await page.screenshot(path=f"pm_{url.split('/')[-1]}.png")

        # Ir directo a settings/payment y hacer clic en Cambiar método de pago
        print("\n--- Probando Cambiar método de pago ---")
        await page.goto("https://ver.flixole.com/settings/payment", wait_until="networkidle")
        await page.wait_for_timeout(1_000)

        cambiar_btn = page.locator('button:has-text("Cambiar método de pago")')
        if await cambiar_btn.count() > 0:
            print("Clic en Cambiar método de pago...")
            await cambiar_btn.click()
            await page.wait_for_timeout(3_000)
            print(f"URL: {page.url}")
            body = await page.inner_text("body")
            print(f"Texto: {body[:500]}")
            buttons = await page.locator("button:visible").all_text_contents()
            print(f"Botones: {[b.strip() for b in buttons if b.strip()]}")
            iframes = await page.locator("iframe").all()
            print(f"Iframes: {len(iframes)}")
            for i, fr in enumerate(iframes):
                title = await fr.get_attribute("title") or ""
                src   = (await fr.get_attribute("src") or "")[:60]
                print(f"  [{i}] title='{title}' src='{src}'")
            await page.screenshot(path="pm_change_method.png")
            print("Captura → pm_change_method.png")

            # Si hay formulario Adyen, rellenar y enviar
            adyen_count = await page.locator('iframe[src*="adyen"], iframe[src*="checkoutshopper"]').count()
            if adyen_count > 0:
                print("\n✅ Formulario Adyen encontrado — rellenando tarjeta de prueba...")
                num_frame = page.frame_locator('iframe[title*="número de tarjeta"]')
                num_input = num_frame.locator('input[placeholder*="1234"]')
                await num_input.click()
                await num_input.type(TARJETA["number"], delay=50)
                await page.wait_for_timeout(500)

                # Nombre del titular
                name_inp = page.locator('input[name="holderName"]')
                if await name_inp.count() > 0:
                    await name_inp.click()
                    await name_inp.type("Juan Perez", delay=50)
                    await page.wait_for_timeout(400)

                exp_frame = page.frame_locator('iframe[title*="caducidad"]')
                exp_input = exp_frame.locator('input[placeholder="MM/AA"]')
                await exp_input.click()
                await exp_input.type(f"{TARJETA['expiry_month']}{TARJETA['expiry_year'][-2:]}", delay=50)
                await page.wait_for_timeout(400)

                cvc_frame = page.frame_locator('iframe[title*="seguridad"]')
                cvc_input = cvc_frame.locator('input[placeholder*="dígitos"]')
                await cvc_input.click()
                await cvc_input.type(TARJETA["cvv"], delay=50)
                await page.wait_for_timeout(1_000)
                await page.screenshot(path="pm_filled.png")
                print("Captura formulario lleno → pm_filled.png")

                # Buscar botón de guardar — específicamente el de Adyen
                save_btn = page.locator('button.adyen-checkout__button--pay').first
                if await save_btn.count() == 0:
                    # Fallback: buscar por texto exacto "Guardar los detalles"
                    save_btn = page.locator('button:has-text("Guardar los detalles")').first
                if await save_btn.count() > 0:
                    print(f"Enviando con botón: {await save_btn.first.inner_text()}")
                    await save_btn.first.click(force=True)
                    await page.wait_for_timeout(8_000)
                    print(f"URL final: {page.url}")
                    body2 = await page.inner_text("body")
                    print(f"Texto final: {body2[:400]}")
                    await page.screenshot(path="pm_result.png")
        else:
            print("No se encontró el botón Cambiar método de pago")

        input("\nPresiona Enter para cerrar...")
        await browser.close()

asyncio.run(main())
