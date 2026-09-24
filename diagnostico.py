"""
Diagnóstico: hace login y explora el flujo de suscripción de FlixOlé.
Imprime URLs, botones y links relevantes para mapear el checkout.
"""
import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

EMAIL    = "rickyzu95@gmail.com"
PASSWORD = "1063171808"

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        page = await browser.new_page()

        # 1) Login
        print(">> Abriendo login...")
        await page.goto("https://ver.flixole.com/log-in", wait_until="networkidle")

        try:
            await page.click("text=Aceptar todo", timeout=5_000)
            print("   Cookies aceptadas")
        except PlaywrightTimeout:
            pass

        await page.fill('input[type="email"]', EMAIL)
        await page.fill('input[type="password"]', PASSWORD)
        await page.screenshot(path="diag_01_before_login.png")

        await page.click('button[type="submit"]')

        try:
            await page.wait_for_function(
                "() => !window.location.href.includes('/log-in')",
                timeout=15_000,
            )
            print(f"   Login OK → {page.url}")
        except PlaywrightTimeout:
            print(f"   TIMEOUT en login, URL actual: {page.url}")
            await page.screenshot(path="diag_02_login_timeout.png")
            await browser.close()
            return

        await page.screenshot(path="diag_02_after_login.png")

        # 2) Explorar URLs comunes de planes/checkout
        test_urls = [
            "https://ver.flixole.com/plans",
            "https://ver.flixole.com/subscribe",
            "https://ver.flixole.com/checkout",
            "https://ver.flixole.com/account",
            "https://ver.flixole.com/account/subscription",
            "https://ver.flixole.com/payment",
        ]

        for url in test_urls:
            await page.goto(url, wait_until="networkidle")
            final_url = page.url
            title = await page.title()
            print(f"\n>> {url}")
            print(f"   Redirigido a: {final_url}")
            print(f"   Título: {title}")

            # Buscar botones visibles
            buttons = await page.locator("button:visible").all_text_contents()
            if buttons:
                print(f"   Botones: {buttons[:10]}")

            # Buscar links relevantes
            links = await page.locator("a[href]").all()
            hrefs = []
            for link in links[:30]:
                href = await link.get_attribute("href")
                if href and any(k in href.lower() for k in ["plan", "subscri", "checkout", "pago", "payment", "account"]):
                    hrefs.append(href)
            if hrefs:
                print(f"   Links relevantes: {hrefs}")

            screenshot_name = url.replace("https://ver.flixole.com/", "").replace("/", "_") or "root"
            await page.screenshot(path=f"diag_{screenshot_name}.png")

        # 3) Desde la home, buscar cómo llegar a planes
        print("\n>> Explorando home...")
        await page.goto("https://ver.flixole.com", wait_until="networkidle")
        print(f"   URL: {page.url}")
        all_buttons = await page.locator("button:visible").all_text_contents()
        print(f"   Botones en home: {all_buttons}")
        all_links = await page.locator("a:visible").all()
        for link in all_links:
            href = await link.get_attribute("href")
            text = await link.inner_text()
            if text.strip():
                print(f"   Link: '{text.strip()}' → {href}")

        await page.screenshot(path="diag_home.png")
        await browser.close()
        print("\n>> Diagnóstico completo. Revisa las capturas diag_*.png")

asyncio.run(main())
