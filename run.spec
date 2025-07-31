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

libcore_path: Path | None = options.libcore_path
if libcore_path is not None and not libcore_path.is_file():
    raise Exception(f"libcore_path: {libcore_path} is not file")

libonnxruntime_path: Path | None = options.libonnxruntime_path
if libonnxruntime_path is not None and not libonnxruntime_path.is_file():
    raise Exception(f"libonnxruntime_path: {libonnxruntime_path} is not file")

core_model_dir_path: Path | None = options.core_model_dir_path
if core_model_dir_path is not None and not core_model_dir_path.is_dir():
    raise Exception(f"core_model_dir_path: {core_model_dir_path} is not dir")


a = Analysis(
    ["run.py"],
    pathex=[],
    binaries=[],
    datas=collect_data_files("pyopenjtalk"),
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

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
    contents_directory="engine_internal",  # 実行時に"sys._MEIPASS"が参照するディレクトリ名
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="run",
)

# 実行ファイルのディレクトリに配置するファイルのコピー

# 実行ファイルと同じrootディレクトリ
target_dir = Path(DISTPATH) / "run"

# リソースをコピー
manifest_file_path = Path("engine_manifest.json")
copy2(manifest_file_path, target_dir)
copytree("resources", target_dir / "resources")

license_file_path = Path("licenses.json")
if license_file_path.is_file():
    copy2("licenses.json", target_dir)

# 動的ライブラリをコピー
if libonnxruntime_path is not None:
    copy2(libonnxruntime_path, target_dir)
if core_model_dir_path is not None:
    copytree(core_model_dir_path, target_dir / "model")
if libcore_path is not None:
    copy2(libcore_path, target_dir)
