"""
Diagnóstico 2: inspecciona los iframes del checkout de confirmación.
"""
import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

EMAIL    = "rickyzu95@gmail.com"
PASSWORD = "1063171808"

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

        # Ir al checkout
        await page.goto("https://ver.flixole.com/checkout", wait_until="networkidle")
        await page.click('text=mensual', timeout=5_000)
        await page.click('button:has-text("Continuar")')
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(3_000)
        print(f"Checkout URL: {page.url}")

        # Listar TODOS los iframes
        iframes = await page.locator("iframe").all()
        print(f"\nTotal iframes: {len(iframes)}")
        for i, fr in enumerate(iframes):
            src   = await fr.get_attribute("src") or "(sin src)"
            name  = await fr.get_attribute("name") or ""
            title = await fr.get_attribute("title") or ""
            cls   = await fr.get_attribute("class") or ""
            print(f"\n  iframe[{i}]:")
            print(f"    src   = {src}")
            print(f"    name  = {name}")
            print(f"    title = {title}")
            print(f"    class = {cls}")

            # Intentar leer inputs dentro del iframe
            try:
                frame = page.frame_locator(f'iframe >> nth={i}')
                inputs = await frame.locator("input").all()
                for inp in inputs:
                    itype = await inp.get_attribute("type") or ""
                    iname = await inp.get_attribute("name") or ""
                    iph   = await inp.get_attribute("placeholder") or ""
                    iac   = await inp.get_attribute("autocomplete") or ""
                    print(f"      input: type={itype} name={iname} placeholder={iph} autocomplete={iac}")
            except Exception as e:
                print(f"      (no se pudo inspeccionar: {e})")

        await page.screenshot(path="diag2_checkout_confirmation.png")
        print("\nCaptura guardada en diag2_checkout_confirmation.png")

        input("Presiona Enter para cerrar el navegador...")
        await browser.close()

asyncio.run(main())
