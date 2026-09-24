"""
Script de diagnóstico: compara el flujo con y sin proxy tomando screenshots en cada paso.
"""
import asyncio
import os
from playwright.async_api import async_playwright

CHROME = os.path.join(os.environ["LOCALAPPDATA"], "ms-playwright", "chromium-1234", "chrome-win64", "chrome.exe")

EMAIL    = "rickyzooo20@gmail.com"
PASSWORD = "1063171808"

PROXY = {
    "server":   "http://gw.dataimpulse.com:823",
    "username": "f0598b258d0d3f429dfe__cr.es",
    "password": "00522fa86bebdbc1",
}

async def run(use_proxy: bool):
    label = "CON_PROXY" if use_proxy else "SIN_PROXY"
    print(f"\n{'='*50}")
    print(f"  Ejecutando: {label}")
    print(f"{'='*50}")

    kwargs = {"headless": False, "executable_path": CHROME}
    if use_proxy:
        kwargs["proxy"] = PROXY

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(**kwargs)
        page = await browser.new_page()

        # 1. Login
        print(f"[1] Navegando a login...")
        await page.goto("https://ver.flixole.com/log-in", wait_until="domcontentloaded")
        await page.screenshot(path=f"debug_{label}_01_login.png")
        print(f"    Screenshot: debug_{label}_01_login.png")

        try:
            await page.click("text=Aceptar todo", timeout=5_000)
        except Exception:
            pass

        await page.fill('input[type="email"]', EMAIL)
        await page.fill('input[type="password"]', PASSWORD)
        await page.screenshot(path=f"debug_{label}_02_filled.png")
        await page.click('button[type="submit"]')

        try:
            await page.wait_for_function(
                "() => !window.location.href.includes('/log-in')", timeout=20_000
            )
            print(f"    Login OK — URL: {page.url}")
        except Exception as e:
            print(f"    Login FAIL: {e}")
            await page.screenshot(path=f"debug_{label}_02_login_fail.png")
            await browser.close()
            return

        # 2. Settings/payment
        print(f"[2] Navegando a settings/payment...")
        await page.goto("https://ver.flixole.com/settings/payment", wait_until="domcontentloaded")
        await page.wait_for_timeout(2_000)
        await page.screenshot(path=f"debug_{label}_03_settings_payment.png")
        print(f"    Screenshot: debug_{label}_03_settings_payment.png — URL: {page.url}")

        # 3. Click Cambiar método de pago
        cambiar_btn = page.locator('button:has-text("Cambiar método de pago")')
        if await cambiar_btn.count() > 0:
            print(f"[3] Haciendo click en 'Cambiar método de pago'...")
            await cambiar_btn.click()
            await page.wait_for_timeout(5_000)
            await page.screenshot(path=f"debug_{label}_04_after_cambiar.png")
            print(f"    Screenshot: debug_{label}_04_after_cambiar.png — URL: {page.url}")
        else:
            print(f"[3] Botón 'Cambiar método de pago' no encontrado")
            await browser.close()
            return

        # 4. Esperar Adyen
        print(f"[4] Esperando iframes de Adyen...")
        for i in range(15):
            await page.wait_for_timeout(1_000)
            count = await page.locator('iframe[src*="adyen"], iframe[src*="checkoutshopper"]').count()
            if count > 0:
                print(f"    Adyen cargado en {i+1}s — {count} iframes")
                break
        else:
            print(f"    Adyen NO cargó en 15s")

        await page.screenshot(path=f"debug_{label}_05_adyen.png")
        print(f"    Screenshot: debug_{label}_05_adyen.png")

        # 5. Listar iframes
        print(f"[5] Iframes en la página:")
        iframes = page.locator('iframe')
        cnt = await iframes.count()
        for i in range(cnt):
            title = await iframes.nth(i).get_attribute('title') or ''
            src   = (await iframes.nth(i).get_attribute('src') or '')[:70]
            print(f"    [{i}] title='{title}' src='{src}'")

        # 6. Intentar click en input del número
        print(f"[6] Intentando interactuar con input de número de tarjeta...")
        selectors = [
            'iframe[title*="número de tarjeta"]',
            'iframe[title*="Utilice Iframe"]',
            'iframe[title*="card number"]',
            'iframe[title*="Card Number"]',
            'iframe[src*="checkoutshopper"]:not([title*="fingerprint"])',
        ]
        for sel in selectors:
            try:
                frame = page.frame_locator(sel)
                inp = frame.locator('input').first
                cnt2 = await inp.count()
                visible = await inp.is_visible() if cnt2 > 0 else False
                print(f"    sel='{sel[:50]}' → count={cnt2} visible={visible}")
                if visible:
                    await page.screenshot(path=f"debug_{label}_06_before_click.png")
                    await inp.click(timeout=5_000)
                    print(f"    ✅ Click exitoso!")
                    await page.screenshot(path=f"debug_{label}_07_after_click.png")
                    break
            except Exception as e:
                print(f"    ❌ {sel[:40]}: {str(e)[:60]}")

        await page.wait_for_timeout(2_000)
        await page.screenshot(path=f"debug_{label}_08_final.png")
        print(f"    Screenshot final: debug_{label}_08_final.png")

        await browser.close()
        print(f"\n  {label} completado.")

async def main():
    await run(use_proxy=False)
    await run(use_proxy=True)

asyncio.run(main())
