"""
Prueba cancelar suscripción y volver a suscribirse inmediatamente.
"""
import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

EMAIL    = "rickyzooo20@gmail.com"
PASSWORD = "1063171808"

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        page    = await browser.new_page()

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
        print(f"Login OK")

        # Ir a Mi Plan
        await page.goto("https://ver.flixole.com/settings/subscription", wait_until="networkidle")
        
        # Verificar si hay plan activo
        body = (await page.inner_text("body")).lower()
        cancel_btn = page.locator('button:has-text("Cancelar el plan")')
        
        if await cancel_btn.count() > 0:
            print("Plan activo encontrado. Cancelando...")
            await cancel_btn.click()
            await page.wait_for_timeout(2_000)
            
            # Puede aparecer un diálogo de confirmación
            buttons = await page.locator("button:visible").all_text_contents()
            print(f"Botones después de cancelar: {[b.strip() for b in buttons if b.strip()]}")
            await page.screenshot(path="cancel_01_after_click.png")
            
            # Si hay confirmación, aceptarla
            confirm = page.locator('button:has-text("Cancelar suscripción")')
            if await confirm.count() > 0:
                await confirm.first.click()
                await page.wait_for_timeout(2_000)
                print("Cancelación confirmada")
            
            await page.wait_for_load_state("networkidle")
            await page.screenshot(path="cancel_02_after_confirm.png")
            
            body2 = await page.inner_text("body")
            print(f"\nEstado tras cancelar:\n{body2[:400]}")
            buttons2 = await page.locator("button:visible").all_text_contents()
            print(f"Botones: {[b.strip() for b in buttons2 if b.strip()]}")
        else:
            print("No hay plan activo para cancelar")

        # Intentar ir al checkout inmediatamente
        print("\nIntentando ir al checkout...")
        await page.goto("https://ver.flixole.com/checkout", wait_until="networkidle")
        await page.wait_for_timeout(2_000)
        print(f"URL: {page.url}")
        body3 = await page.inner_text("body")
        print(body3[:400])
        buttons3 = await page.locator("button:visible").all_text_contents()
        print(f"Botones: {[b.strip() for b in buttons3 if b.strip()]}")
        await page.screenshot(path="cancel_03_checkout.png")

        input("\nPresiona Enter para cerrar...")
        await browser.close()

asyncio.run(main())
