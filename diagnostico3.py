"""
Diagnóstico 3: hace el flujo completo y muestra el texto de la página
después de enviar el pago, para mapear las keywords correctas de Adyen.
"""
import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

EMAIL    = "rickyzu95@gmail.com"
PASSWORD = "1063171808"

# Pon aquí UNA de tus tarjetas reales para ver qué responde Adyen
CARD = {
    "number":       "4111111111111111",
    "expiry_month": "12",
    "expiry_year":  "2027",
    "cvv":          "123",
    "name":         "Juan Perez",
}

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        page = await browser.new_page()

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

        # Checkout
        await page.goto("https://ver.flixole.com/checkout", wait_until="networkidle")
        await page.click('text=mensual', timeout=5_000)
        await page.click('button:has-text("Continuar")')
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2_000)
        print(f"Checkout: {page.url}")

        # Rellenar tarjeta con Adyen iframes
        print("Rellenando número...")
        num_frame = page.frame_locator('iframe[title*="número de tarjeta"]')
        await num_frame.locator('input[placeholder*="1234"]').fill(CARD["number"])

        print("Rellenando fecha...")
        exp_frame = page.frame_locator('iframe[title*="caducidad"]')
        expiry = f"{CARD['expiry_month']}/{CARD['expiry_year'][-2:]}"
        await exp_frame.locator('input[placeholder="MM/AA"]').fill(expiry)

        print("Rellenando CVV...")
        cvc_frame = page.frame_locator('iframe[title*="seguridad"]')
        await cvc_frame.locator('input[placeholder*="dígitos"]').fill(CARD["cvv"])

        await page.screenshot(path="diag3_before_submit.png")
        print("Captura antes de enviar → diag3_before_submit.png")

        # Enviar
        print("Enviando pago...")
        submit = page.locator(
            'button:has-text("Confirmar"), button:has-text("Pagar"), '
            'button:has-text("Suscribir"), button[type="submit"]'
        ).last
        await submit.click()

        # Esperar respuesta
        await page.wait_for_timeout(5_000)
        try:
            await page.wait_for_load_state("networkidle", timeout=15_000)
        except PlaywrightTimeout:
            pass

        print(f"\nURL final: {page.url}")

        await page.screenshot(path="diag3_after_submit.png")
        print("Captura después de enviar → diag3_after_submit.png")

        # Mostrar TODO el texto visible
        body = await page.inner_text("body")
        print(f"\n{'='*60}")
        print("TEXTO VISIBLE EN PANTALLA:")
        print('='*60)
        print(body[:1000])
        print('='*60)

        # Mostrar todos los botones visibles
        botones = await page.locator("button:visible").all_text_contents()
        print(f"\nBotones visibles: {botones}")

        input("\nPresiona Enter para cerrar...")
        await browser.close()

asyncio.run(main())
