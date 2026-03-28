# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for the update bootstrap (one-file, stdlib only).
Build with: pyinstaller update_bootstrap.spec
"""

block_cipher = None

a = Analysis(
    ['app/backend/update_bootstrap.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='update_bootstrap',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=None,
)
