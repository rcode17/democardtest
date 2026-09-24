import asyncio
from playwright.async_api import async_playwright

CHROME = r'C:\Users\rjayala\AppData\Local\ms-playwright\chromium-1234\chrome-win64\chrome.exe'
PROXY = {
    "server":   "http://gw.dataimpulse.com:823",
    "username": "f0598b258d0d3f429dfe__cr.es",
    "password": "00522fa86bebdbc1",
}

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False, executable_path=CHROME, proxy=PROXY)
        page = await browser.new_page()

        await page.goto("https://ver.flixole.com/log-in", wait_until="domcontentloaded")
        await page.fill('input[type="email"]', "rickyzooo20@gmail.com")
        await page.fill('input[type="password"]', "1063171808")
        await page.click('button[type="submit"]')
        await page.wait_for_function("() => !window.location.href.includes('/log-in')", timeout=20000)
        print("Login OK")

        await page.goto("https://ver.flixole.com/settings/payment", wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        cambiar_btn = page.locator('button:has-text("Cambiar método de pago")')
        await cambiar_btn.wait_for(state="visible", timeout=10000)
        print("Botón encontrado, haciendo click...")
        await cambiar_btn.click()

        # Monitorear URL e iframes cada segundo por 30s
        for i in range(30):
            await page.wait_for_timeout(1000)
            url = page.url
            iframe_count = await page.locator('iframe[src*="adyen"], iframe[src*="checkoutshopper"]').count()
            all_iframes = await page.locator('iframe').count()
            print(f"  [{i+1}s] URL={url} | adyen_iframes={iframe_count} | all_iframes={all_iframes}")
            if iframe_count > 0:
                print("  ✅ Adyen cargó!")
                await page.screenshot(path="debug_after_click_adyen.png")
                break
            if i % 5 == 4:
                await page.screenshot(path=f"debug_after_click_{i+1}s.png")
                print(f"  Screenshot: debug_after_click_{i+1}s.png")

        await browser.close()

asyncio.run(main())
