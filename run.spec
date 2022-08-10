# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
import os

datas = collect_data_files('pyopenjtalk')


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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='run',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

datas = [
    ('engine_manifest_assets', 'engine_manifest_assets', 'DATA'),
    ('speaker_info', 'speaker_info', 'DATA'),
    ('default.csv', 'default.csv', 'DATA'),
    ('licenses.json', 'licenses.json', 'DATA'),
    ('presets.yaml', 'presets.yaml', 'DATA'),
]

# コアとONNX Runtimeはバイナリであるが、`binaries`に加えると
# 依存関係のパスがPyInstallerに書き換えらるので、`datas`に加える
# 参考: https://github.com/VOICEVOX/voicevox_engine/pull/446#issuecomment-1210052318
libcore_path = os.environ.get('LIBCORE_PATH')
if libcore_path:
    print('LIBCORE_PATH is found:', libcore_path)
    if not os.path.isfile(libcore_path):
        raise Exception("LIBCORE_PATH was found, but it is not file!")
    filename = os.path.basename(libcore_path)
    datas += [(filename, libcore_path, 'DATA')]

libonnxruntime_path = os.environ.get('LIBONNXRUNTIME_PATH')
if libonnxruntime_path:
    print('LIBONNXRUNTIME_PATH is found:', libonnxruntime_path)
    if not os.path.isfile(libonnxruntime_path):
        raise Exception("LIBCORE_PATH was found, but it is not file!")
    filename = os.path.basename(libonnxruntime_path)
    datas += [(filename, libonnxruntime_path, 'DATA')]

coll = COLLECT(
    exe,
    [],
    [],
    datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='run',
)
