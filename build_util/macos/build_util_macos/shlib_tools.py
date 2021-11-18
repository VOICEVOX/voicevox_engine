import subprocess
from pathlib import Path
from typing import List


def get_dylib_paths(base_path: Path) -> List[Path]:
    """base_path以下の全てのサブディレクトリにあるdylibファイルのリストを返す"""
    return list(base_path.glob("**/*.dylib"))


def get_rpaths(shared_lib_path: Path) -> List[Path]:
    """引数で指定された共有ライブラリのrpathのリストを返す"""
    proc = subprocess.run(["otool", "-L", str(shared_lib_path)], stdout=subprocess.PIPE)
    output = proc.stdout.decode("utf-8")
    paths = [
        Path(line.lstrip().split(" ", maxsplit=1)[0])
        for line in output.splitlines()[1:]
    ]
    # 得られたパスのリストのうち、共有ライブラリ自体とライブラリ名が同じものは
    # rpath ではなく install ID というものなので除外
    return [
        path
        for path in paths
        if path.name.split(".")[0] != shared_lib_path.name.split(".")[0]
    ]


def is_distributable_rpath(rpath: Path) -> bool:
    """開発環境にインストールされたパッケージに依存しないrpathかどうか"""
    # 以下のプレフィックスで始まるrpathは配布に際して問題がない
    # - プレースホルダ。実行時に自動で解決される
    #   - @executable_path/
    #   - @loader_path/
    #   - @rpath/
    # - システム標準のライブラリがあるディレクトリ
    #   - /usr/lib/
    #   - /System/Library/Frameworks/
    #   - /System/Library/PrivateFrameworks/
    DISTRIBUTABLE_PREFIXES = [
        "@executable_path/",
        "@loader_path/",
        "@rpath/",
        "/usr/lib/",
        "/System/Library/Frameworks/",
        "/System/Library/PrivateFrameworks/",
    ]
    result = False

    for prefix in DISTRIBUTABLE_PREFIXES:
        if str(rpath).startswith(prefix):
            result = True
            break
        else:
            continue

    return result


def change_rpath(old_rpath: Path, new_rpath: Path, dylib_path: Path, base_path: Path):
    """dylib_pathで指定されたdylibのrpathを、old_rpathから、new_rpath（base_pathからの相対パスに変換したもの）に変更する"""
    relative_new_rpath = new_rpath.relative_to(base_path)
    subprocess.run(
        [
            "install_name_tool",
            "-change",
            old_rpath,
            "@rpath/" + str(relative_new_rpath),
            dylib_path,
        ]
    )


class SharedLib:
    """共有ライブラリの情報"""

    __path: Path
    __rpaths: List[Path]

    def __init__(self, shared_lib_path: Path):
        self.__path = shared_lib_path
        self.__rpaths = get_rpaths(shared_lib_path)

    @property
    def path(self) -> Path:
        return self.__path

    def get_non_distributable_rpaths(self) -> List[Path]:
        """rpathのうち、開発環境に依存しているもののリスト"""
        return [rpath for rpath in self.__rpaths if not is_distributable_rpath(rpath)]
