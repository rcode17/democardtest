# -*- mode: python ; coding: utf-8 -*-
import os

chromium_src = os.path.join(
    os.environ["LOCALAPPDATA"], "ms-playwright", "chromium-1234", "chrome-win64"
)

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('icon.ico', '.'),
        ('logo.png', '.'),
        (chromium_src, 'chromium-1234/chrome-win64'),
    ],
    hiddenimports=[
        'playwright',
        'playwright.async_api',
        'customtkinter',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='CardChecker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon.ico'],
)
