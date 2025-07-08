# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_submodules

# Get the current working directory
base_path = os.path.abspath(".")

# Collect files to include (payload folder and config.json)
datas = [
    (os.path.join(base_path, 'config.json'), '.'),  # config.json to root of .exe
    (os.path.join(base_path, 'payload'), 'payload')  # whole payload folder
]

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[base_path],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
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
    name='GameDiscBurner',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # True = show terminal window; False = GUI-only
    icon='icon.ico'  # or None if no icon
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='GameDiscBurner'
)
