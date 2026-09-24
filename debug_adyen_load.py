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

        # Aceptar cookies
        for _ in range(5):
            try:
                accept = page.locator('button:has-text("Aceptar todo")').first
                if await accept.count() > 0:
                    await accept.click(timeout=2000)
                    print("Cookies aceptadas")
                    await page.wait_for_timeout(1000)
                    break
            except Exception:
                pass
            await page.wait_for_timeout(1000)

        # Click cambiar método de pago
        cambiar = page.locator('button:has-text("Cambiar método de pago")')
        await cambiar.wait_for(state="visible", timeout=10000)
        await cambiar.click()
        print("Click en Cambiar método de pago")

        # Aceptar cookies si aparece de nuevo
        for _ in range(8):
            await page.wait_for_timeout(1000)
            try:
                accept = page.locator('button:has-text("Aceptar todo")').first
                if await accept.count() > 0:
                    await accept.click(timeout=2000)
                    print(f"Cookies aceptadas (post-click)")
                    await page.wait_for_timeout(1000)
                    break
            except Exception:
                pass

        # Monitorear cada segundo hasta que el input esté listo
        print("\nEsperando que Adyen cargue el input...")
        for i in range(60):
            await page.wait_for_timeout(1000)

            # Listar iframes cada 5s
            iframes = page.locator('iframe')
            cnt = await iframes.count()

            if i % 5 == 0 or cnt > 0:
                print(f"\n[{i+1}s] Total iframes: {cnt}")
                for j in range(cnt):
                    try:
                        title = await iframes.nth(j).get_attribute('title') or ''
                        src   = (await iframes.nth(j).get_attribute('src') or '')[:60]
                        print(f"  [{j}] title='{title}' src='{src}'")
                    except Exception:
                        pass

            # Probar todos los iframes con inputs
            for j in range(cnt):
                try:
                    title = await iframes.nth(j).get_attribute('title') or ''
                    src   = await iframes.nth(j).get_attribute('src') or ''
                    if 'checkoutshopper' in src or 'adyen' in src:
                        frame = page.frame_locator(f'iframe[src="{src}"]')
                        inputs = frame.locator('input')
                        inp_cnt = await inputs.count()
                        if inp_cnt > 0:
                            visible = await inputs.first.is_visible()
                            print(f"  ✅ iframe[{j}] title='{title}' tiene {inp_cnt} inputs visible={visible}")
                            if visible:
                                await page.screenshot(path="debug_adyen_ready.png")
                                print(f"  Screenshot: debug_adyen_ready.png")
                                await browser.close()
                                return
                except Exception as e:
                    pass

        print("Timeout — Adyen nunca cargó el input")
        await page.screenshot(path="debug_adyen_timeout.png")
        await browser.close()

asyncio.run(main())
