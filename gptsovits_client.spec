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
import httpx
#shutil.copytree('ref_audios','dist/gptsovits/ref_audios')
os.makedirs('dist/gptsovits/ref_audios')
shutil.copy2(
    "ref_audios/00_06_27_Rarity_Happy__Well, yes, they may look the same, but i know it's older, And that's what makes it so much more divine!.flac",
    'dist/gptsovits/ref_audios')
shutil.copy2(
    "ref_audios/00_03_24_Pinkie_Happy_Noisy_There's a chance i may have missed a note or two Here or there, but i just love playing so much!.flac",
    'dist/gptsovits/ref_audios')
shutil.copy2(
    "ref_audios/00_06_18_Applejack_Neutral_Noisy_Well, if your parents won't stand up for themselves, Maybe you need to stand up for them..flac",
    'dist/gptsovits/ref_audios')
shutil.copy2(
    "ref_audios/00_14_11_Fluttershy_Anxious__You're ever so thoughtful to share your special bonding ritual with us but, uh..flac",
    'dist/gptsovits/ref_audios')
shutil.copy2(
    "ref_audios/00_00_16_Rainbow_Neutral_Noisy_So, now that you know the elements of a good cheer, let's hear one!.flac",
    'dist/gptsovits/ref_audios')
shutil.copy2(
    "ref_audios/00_01_23_Twilight_Neutral__which means you'll have the opportunity to live your dream as a wonderbolt!.flac",
    'dist/gptsovits/ref_audios')
shutil.copytree('models','dist/gptsovits/models')
shutil.copy2('ts_cursor.png','dist/gptsovits/ts_cursor.png')

# Download ffmpeg and ffprobe if they do not already exist
if not os.path.exists('ffmpeg.exe'):
    r = httpx.get("https://huggingface.co/lj1995/VoiceConversionWebUI/resolve/main/ffmpeg.exe?download=true")
    r : httpx.Response
    if r.status_code == 200:
        with open('ffmpeg.exe', 'wb') as file:
            file.write(r.content)
if not os.path.exists('ffprobe.exe'):
    r = httpx.get("https://huggingface.co/lj1995/VoiceConversionWebUI/resolve/main/ffmpeg.exe?download=true")
    if r.status_code == 200:
        with open('ffprobe.exe', 'wb') as file:
            file.write(r.content)

shutil.copy2('ffmpeg.exe','dist/gptsovits/ffmpeg.exe')
shutil.copy2('ffprobe.exe','dist/gptsovits/ffprobe.exe')