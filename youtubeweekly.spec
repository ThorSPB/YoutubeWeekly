# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for YoutubeWeekly.
Build with: pyinstaller youtubeweekly.spec
"""

import os
import platform

block_cipher = None

# Platform-specific data files for bundled executables
datas = [
    ('config', 'config'),
    ('docs', 'docs'),
    ('app/frontend/assets', 'app/frontend/assets'),
]

# Add platform-specific player/tools if they exist
if os.path.exists('app/player'):
    datas.append(('app/player', 'app/player'))
if os.path.exists('app/tools'):
    datas.append(('app/tools', 'app/tools'))

# Hidden imports that PyInstaller might miss
hiddenimports = [
    'plyer.platforms.linux',
    'plyer.platforms.linux.notification',
    'plyer.platforms.win',
    'plyer.platforms.win.notification',
    'plyer.platforms.macosx',
    'plyer.platforms.macosx.notification',
    'pystray._xorg',
    'pystray._win32',
    'pystray._darwin',
    'PIL._tkinter_finder',
]

a = Analysis(
    ['app/frontend/gui.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='YoutubeWeekly',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app/frontend/assets/icon4.ico' if os.path.exists('app/frontend/assets/icon4.ico') else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='YoutubeWeekly',
)
