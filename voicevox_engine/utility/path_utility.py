import os
import sys
import traceback
from pathlib import Path
from typing import Literal

from platformdirs import user_data_dir


def runtime_type() -> Literal["nuitka", "pyinstaller", "python"]:
    """
    コンパイルに使用したライブラリ名を返す。
    コンパイルしていない場合は"python"を返す。
    """
    # nuitkaビルドをした際はグローバルに__compiled__が含まれる
    if "__compiled__" in globals():
        return "nuitka"

    # pyinstallerでビルドをした際はsys.frozenが設定される
    elif getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return "pyinstaller"

    return "python"


def engine_root() -> Path:
    runtime = runtime_type()
    if runtime == "nuitka":
        root_dir = Path(sys.argv[0]).parent

    elif runtime == "pyinstaller":
        root_dir = Path(sys.executable).parent

    else:
        root_dir = Path(__file__).parents[2]

    return root_dir.resolve(strict=True)


def internal_root() -> Path:
    root_dir = Path(__file__).parents[2]
    return root_dir.resolve(strict=True)


def is_development() -> bool:
    """
    開発版かどうか判定する関数
    Nuitka/Pyinstallerでコンパイルされていない場合は開発環境とする。
    """
    return runtime_type() == "python"


def get_save_dir():
    # FIXME: ファイル保存場所をエンジン固有のIDが入ったものにする
    # FIXME: Windowsは`voicevox-engine/voicevox-engine`ディレクトリに保存されているので
    # `VOICEVOX/voicevox-engine`に変更する
    if is_development():
        app_name = "voicevox-engine-dev"
    else:
        app_name = "voicevox-engine"
    return Path(user_data_dir(app_name))


def delete_file(file_path: str) -> None:
    try:
        os.remove(file_path)
    except OSError:
        traceback.print_exc()
