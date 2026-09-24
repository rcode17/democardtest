"""
Debug registro + checkout completo
"""
import asyncio, random, string
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

def random_email():
    return ''.join(random.choices(string.ascii_lowercase+string.digits, k=10)) + "@gmail.com"

def random_password():
    return ''.join(random.choices(string.ascii_letters+string.digits, k=10)) + "Aa1!"

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        page = await browser.new_page()

        email    = random_email()
        password = random_password()
        print(f"Registrando: {email}")

        # Registro
        await page.goto("https://ver.flixole.com/create-account", wait_until="networkidle")
        try:
            await page.click("text=Aceptar todo", timeout=5_000)
            await page.wait_for_timeout(500)
        except PlaywrightTimeout:
            pass

        for inp in await page.locator('input[type="email"]').all():
            await inp.fill(email)
        await page.fill('input[type="password"]', password)

        # Clic en CREAR
        all_btns = await page.locator("button:visible").all()
        for b in reversed(all_btns):
            txt = (await b.inner_text()).strip().upper()
            if "CREAR" in txt:
                print(f"Clic en botón: {txt}")
                await b.click()
                break

        await page.wait_for_timeout(3_000)
        print(f"URL tras registro: {page.url}")
        await page.screenshot(path="dreg_01_after_register.png")

        # Ver qué hay en el checkout
        body = await page.inner_text("body")
        print(f"\nContenido:\n{body[:500]}")
        buttons = await page.locator("button:visible").all_text_contents()
        print(f"\nBotones: {[b.strip() for b in buttons if b.strip()]}")

        # Intentar seleccionar mensual
        print("\n--- Intentando seleccionar plan mensual ---")
        m = page.locator('text=mensual').first
        if await m.count() > 0:
            await m.click(timeout=5_000)
            print("Plan mensual clickeado")
        await page.wait_for_timeout(1_000)

        buttons2 = await page.locator("button:visible").all_text_contents()
        print(f"Botones después de seleccionar mensual: {[b.strip() for b in buttons2 if b.strip()]}")
        await page.screenshot(path="dreg_02_after_plan.png")

        # Clic en Continuar
        btn = page.locator('button:has-text("Continuar")').first
        if await btn.count() > 0:
            await btn.click()
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(2_000)
            print(f"URL tras Continuar: {page.url}")
            await page.screenshot(path="dreg_03_after_continuar.png")
            
            # Verificar iframes de Adyen
            iframes = await page.locator("iframe").all()
            print(f"Iframes: {len(iframes)}")
            for i, fr in enumerate(iframes):
                title = await fr.get_attribute("title") or ""
                src = (await fr.get_attribute("src") or "")[:60]
                print(f"  [{i}] title='{title}'  src='{src}'")
        else:
            print("No se encontró botón Continuar")

        input("\nPresiona Enter para cerrar...")
        await browser.close()

asyncio.run(main())
