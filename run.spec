# -*- mode: python ; coding: utf-8 -*-
# このファイルはPyInstallerによって自動生成されたもので、それをカスタマイズして使用しています。
from PyInstaller.utils.hooks import collect_data_files
import os

datas = [
    ('engine_manifest_assets', 'engine_manifest_assets'),
    ('speaker_info', 'speaker_info'),
    ('default.csv', '.'),
    ('licenses.json', '.'),
    ('presets.yaml', '.'),
]
datas += collect_data_files('pyopenjtalk')

# コアとONNX Runtimeはバイナリであるが、`binaries`に加えると
# 依存関係のパスがPyInstallerに書き換えらるので、`datas`に加える
# 参考: https://github.com/VOICEVOX/voicevox_engine/pull/446#issuecomment-1210052318
libcore_path = os.environ.get('LIBCORE_PATH')
if libcore_path:
    print('LIBCORE_PATH is found:', libcore_path)
    if not os.path.isfile(libcore_path):
        raise Exception("LIBCORE_PATH was found, but it is not file!")
    datas += [(libcore_path, ".")]

libonnxruntime_path = os.environ.get('LIBONNXRUNTIME_PATH')
if libonnxruntime_path:
    print('LIBONNXRUNTIME_PATH is found:', libonnxruntime_path)
    if not os.path.isfile(libonnxruntime_path):
        raise Exception("LIBCORE_PATH was found, but it is not file!")
    datas += [(libonnxruntime_path, ".")]


block_cipher = None


a = Analysis(
    ['run.py'],
    pathex=[],
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
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='run',
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
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='run',
)
