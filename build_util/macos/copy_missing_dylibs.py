"""
配布物内の.dylibファイルの不足を解消するためのスクリプト

引数で指定したbase_directory以下にある.dylibファイルのrpathをチェックし、
rpathの指す.dylibファイルがbase_directory以下に存在しなかった場合、
rpathの指している場所からその.dylibファイルをbase_directory直下へとコピーする。
"""

import argparse
import shutil
import sys
from pathlib import Path
from typing import List, Set

from build_util_macos.shlib_tools import SharedLib, get_dylib_paths

parser = argparse.ArgumentParser()
parser.add_argument(
    "base_directory", help="copy the missing dylibs under base_directory", type=str
)
args = parser.parse_args()
base_dir_path = Path(args.base_directory)

if not (base_dir_path.exists() and base_dir_path.is_dir()):
    print("could not find the directory:", str(base_dir_path), file=sys.stderr)
    exit(1)

# base_dir_path以下の全てのサブディレクトリを探索して得たdylibのリスト
dylib_paths: List[Path] = get_dylib_paths(base_dir_path)
# 全てのdylibのファイル名のリスト
dylib_names: List[str] = [path.name for path in dylib_paths]

# 開発環境に依存したrpathを持つdylibのリスト
non_distributable_dylibs: List[SharedLib] = []
for dylib_path in dylib_paths:
    lib = SharedLib(dylib_path)
    if lib.get_non_distributable_rpaths():
        non_distributable_dylibs.append(lib)

# 開発環境に依存したrpathの集合
non_distributable_rpaths: Set[Path] = set()
for dylib in non_distributable_dylibs:
    rpaths: Set[Path] = set([rpath for rpath in dylib.get_non_distributable_rpaths()])
    non_distributable_rpaths = non_distributable_rpaths.union(rpaths)

# rpathが指しているdylibのうち、base_dir_path以下に存在しないもののリスト
external_dylib_paths: List[Path] = []
for rpath in non_distributable_rpaths:
    if not (rpath.name in dylib_names):
        external_dylib_paths.append(rpath)

# 不足しているdylibをbase_dir_path直下にコピー
for dylib_path in external_dylib_paths:
    shutil.copy(dylib_path, base_dir_path, follow_symlinks=True)
