# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

datas = []
datas.extend(collect_data_files('gradio_client'))
datas.extend(collect_data_files('py3langid'))
datas.append(('tools/i18n/locale', 'tools/i18n/locale'))
datas.append(('GPT_SoVITS/text', 'text'))
datas.extend(collect_data_files('jieba_fast'))

a = Analysis(
    ['gui_server.py'],
    pathex=['GPT_SoVITS'],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    module_collection_mode={
        'gradio': 'py',
    }
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='gptsovits_server',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='gptsovits_server',
)
import os
import shutil