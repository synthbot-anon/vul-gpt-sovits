# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

datas = []
datas.extend(collect_data_files('gradio_client'))
datas.extend(collect_data_files('py3langid'))
datas.append(('tools/i18n/locale', 'tools/i18n/locale'))
datas.append(('GPT_SoVITS/text', 'text'))
datas.extend(collect_data_files('jieba_fast'))
datas.extend(collect_data_files('g2p_en'))
datas.extend(collect_data_files('wordsegment'))

a = Analysis(
    ['gui_client.py'],
    pathex=['GPT_SoVITS'],
    binaries=[],
    datas=datas,
    hiddenimports=['uvicorn.lifespan.off','uvicorn.lifespan.on','uvicorn.lifespan',
'uvicorn.protocols.websockets.auto','uvicorn.protocols.websockets.wsproto_impl',
'uvicorn.protocols.websockets_impl','uvicorn.protocols.http.auto',
'uvicorn.protocols.http.h11_impl','uvicorn.protocols.http.httptools_impl',
'uvicorn.protocols.websockets','uvicorn.protocols.http','uvicorn.protocols',
'uvicorn.loops.auto','uvicorn.loops.asyncio','uvicorn.loops.uvloop','uvicorn.loops',
'uvicorn.logging', 'gui_server', 'wordsegment', 'g2p_en'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    module_collection_mode={
        'gradio': 'py',
        'inflect': 'pyz+py'
    }
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='gptsovits',
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
    name='gptsovits',
)
import os
import shutil
shutil.copytree('ref_audios','dist/gptsovits/ref_audios')
shutil.copytree('models','dist/gptsovits/models')
shutil.copy2('ts_cursor.png','dist/gptsovits/ts_cursor.png')