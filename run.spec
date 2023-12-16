# -*- mode: python ; coding: utf-8 -*-
# このファイルはPyInstallerによって自動生成されたもので、それをカスタマイズして使用しています。
from argparse import ArgumentParser
from pathlib import Path
from shutil import copy2, copytree

from PyInstaller.utils.hooks import collect_data_files

parser = ArgumentParser()
parser.add_argument("--libcore_path", type=Path)
parser.add_argument("--libonnxruntime_path", type=Path)
parser.add_argument("--core_model_dir_path", type=Path)
options = parser.parse_args()

libonnxruntime_path: Path | None = options.libonnxruntime_path
if libonnxruntime_path is not None and not libonnxruntime_path.is_file():
    raise Exception(f"libonnxruntime_path: {libonnxruntime_path} is not file")

libcore_path: Path | None = options.libcore_path
if libcore_path is not None and not libcore_path.is_file():
    raise Exception(f"libcore_path: {libcore_path} is not file")

core_model_dir_path: Path | None = options.core_model_dir_path
if core_model_dir_path is not None and not core_model_dir_path.is_dir():
    raise Exception(f"core_model_dir_path: {core_model_dir_path} is not dir")

datas = [
    ("default.csv", "."),
    ("presets.yaml", "."),
    ("ui_template", "ui_template"),
]
datas += collect_data_files("pyopenjtalk")


block_cipher = None


a = Analysis(
    ["run.py"],
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
    name="run",
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
    contents_directory="engine_internal",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="run",
)

# 実行ファイル作成後の処理
target_dir = Path(DISTPATH) / "run"

if libonnxruntime_path is not None:
    copy2(libonnxruntime_path, target_dir)

if libcore_path is not None:
    copy2(libcore_path, target_dir)

if core_model_dir_path is not None:
    copytree(core_model_dir_path, target_dir / "model")

license_file_path = Path("licenses.json")
if license_file_path.is_file():
    copy2("licenses.json", target_dir)

copytree("speaker_info", target_dir / "speaker_info")
copy2("engine_manifest.json", target_dir)
copytree("engine_manifest_assets", target_dir / "engine_manifest_assets")
