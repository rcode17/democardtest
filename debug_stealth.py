"""
Prueba playwright-stealth para bypassear reCAPTCHA en registro de FlixOlé.
"""
import asyncio, random, string
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

def random_email():
    return ''.join(random.choices(string.ascii_lowercase+string.digits, k=10)) + "@gmail.com"

def random_password():
    return ''.join(random.choices(string.ascii_letters+string.digits, k=10)) + "Aa1!"

async def main():
    email    = random_email()
    password = random_password()
    print(f"Registrando con stealth + Chrome real: {email}")

    async with async_playwright() as pw:
        # Usar Chrome real instalado — mejor score de reCAPTCHA que Chromium de Playwright
        browser = await pw.chromium.launch(
            headless=False,
            executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
            ]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            locale="es-ES",
        )
        page = await context.new_page()

        # Aplicar stealth
        await Stealth().apply_stealth_async(page)

        await page.goto("https://ver.flixole.com/create-account", wait_until="networkidle")
        try:
            await page.click("text=Aceptar todo", timeout=5_000)
            await page.wait_for_timeout(800)
        except Exception:
            pass

        # Rellenar con delays humanos
        for inp in await page.locator('input[type="email"]').all():
            await inp.click()
            await page.wait_for_timeout(random.randint(300, 600))
            await inp.type(email, delay=random.randint(50, 120))
            await page.wait_for_timeout(random.randint(200, 500))

        await page.locator('input[type="password"]').click()
        await page.wait_for_timeout(random.randint(300, 500))
        await page.locator('input[type="password"]').type(password, delay=random.randint(50, 100))
        await page.wait_for_timeout(random.randint(500, 1200))

        # Clic en CREAR
        all_btns = await page.locator("button:visible").all()
        for b in reversed(all_btns):
            txt = (await b.inner_text()).strip().upper()
            if "CREAR" in txt:
                await b.click()
                break

        await page.wait_for_timeout(4_000)
        print(f"URL tras registro: {page.url}")
        body = (await page.inner_text("body")).lower()

        if "captcha" in body or "robot" in body:
            print("❌ reCAPTCHA bloqueó el registro")
        elif "checkout" in page.url:
            print("✅ REGISTRO EXITOSO con stealth")
        else:
            print(f"⚠ Resultado desconocido: {page.url}")
            print(body[:300])

        await page.screenshot(path="stealth_result.png")
        input("Presiona Enter para cerrar...")
        await browser.close()

asyncio.run(main())
