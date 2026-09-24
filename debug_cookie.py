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

        # Buscar todos los botones del banner de cookies
        btns = page.locator('[class*="cky"] button, [class*="cookie"] button, [class*="consent"] button, [class*="privacy"] button')
        cnt = await btns.count()
        print(f"Botones en banner de cookies: {cnt}")
        for i in range(cnt):
            txt = await btns.nth(i).inner_text()
            cls = await btns.nth(i).get_attribute("class") or ""
            print(f"  [{i}] text={repr(txt)} class={cls[:60]}")

        await page.screenshot(path="debug_cookie_banner.png")
        print("Screenshot: debug_cookie_banner.png")
        await browser.close()

asyncio.run(main())
