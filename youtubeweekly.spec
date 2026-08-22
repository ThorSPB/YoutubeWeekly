# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for YoutubeWeekly.
Build with: pyinstaller youtubeweekly.spec
"""
import os
import sys

# The .ico carries every size Windows asks for (16-256) and the .icns is the
# high-resolution master both are generated from - see scripts/build_icon.py.
# macOS wants the .icns natively rather than a converted .ico.
APP_ICON = os.path.join("app", "frontend", "assets",
                        "icon4.icns" if sys.platform == "darwin" else "icon4.ico")

block_cipher = None

a = Analysis(
    [os.path.join("app", "frontend", "gui.py")],
    pathex=["."],
    binaries=[],
    datas=[
        ("config", "config"),
        ("app/player", "app/player"),
        ("app/tools", "app/tools"),
        ("app/frontend/assets", "assets"),
        ("docs", "docs"),
    ],
    hiddenimports=[
        "yt_dlp",
        "plyer",
        "plyer.platforms.win.notification",
        "plyer.platforms.linux.notification",
        "plyer.platforms.macosx.notification",
        "tkinter",
        "requests",
        "certifi",
        "charset_normalizer",
        "idna",
        "urllib3",
        "pystray",
        "pystray._xorg",
        "pystray._win32",
        "pystray._darwin",
        "PIL._tkinter_finder",
        "PIL.ImageTk",   # window icons: iconphoto() needs a Tk PhotoImage
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="YoutubeWeekly",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=APP_ICON,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="YoutubeWeekly",
)
