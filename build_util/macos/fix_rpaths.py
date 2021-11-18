"""
配布物内の.dylibファイルのrpathをどのようなユーザー環境においても有効になるように修正するスクリプト

引数で指定したbase_directory以下にある.dylibファイルのrpathをチェックし、
開発環境に依存した（配布先の環境に存在することが保証されていない）rpathであった場合、
base_directory以下の.dylibファイルを相対パスで指すように変更する。
（base_directory以下の.dylibファイルに不足がないことを前提とする。）
"""

import argparse
import sys
from pathlib import Path
from typing import List, Set

from build_util_macos.shlib_tools import SharedLib, change_rpath, get_dylib_paths

parser = argparse.ArgumentParser()
parser.add_argument(
    "base_directory", help="fix the rpaths of the dylibs under base_directory", type=str
)
args = parser.parse_args()
base_dir_path = Path(args.base_directory)

if not (base_dir_path.exists() and base_dir_path.is_dir()):
    print("could not find the directory:", str(base_dir_path), file=sys.stderr)
    exit(1)

# base_dir_path以下の全てのサブディレクトリを探索して得たdylibのリスト
internal_dylib_paths: List[Path] = get_dylib_paths(base_dir_path)
# 全てのdylibのファイル名のリスト
internal_dylib_names: List[str] = [path.name for path in internal_dylib_paths]

# 開発環境に依存したrpathを持つdylibのリスト
non_distributable_dylibs: List[SharedLib] = []
for internal_dylib_path in internal_dylib_paths:
    lib = SharedLib(internal_dylib_path)
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
    if not (rpath.name in internal_dylib_names):
        external_dylib_paths.append(rpath)

# base_dir_path以下でdylibが不足している場合は、不足しているdylibを表示して終了
if external_dylib_paths:
    print(
        f"following dylibs not found under base_dir_path ({str(base_dir_path)}):",
        file=sys.stderr,
    )
    for path in external_dylib_paths:
        print(f"\t{path.name}", file=sys.stderr)
    exit(1)

# 開発環境に依存したrpathを、base_dir_path以下のdylibを指すように変更
for dylib in non_distributable_dylibs:
    for rpath in dylib.get_non_distributable_rpaths():
        for internal_dylib_path in internal_dylib_paths:
            if internal_dylib_path.name == rpath.name:
                change_rpath(rpath, internal_dylib_path, dylib.path, base_dir_path)
