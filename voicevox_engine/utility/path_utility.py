import os
import sys
import traceback
from pathlib import Path

from platformdirs import user_data_dir


def engine_root() -> Path:
    if is_development():
        root_dir = Path(__file__).parents[2]

    # Nuitka/Pyinstallerでビルドされている場合
    else:
        root_dir = Path(sys.argv[0]).parent

    return root_dir.resolve(strict=True)


def is_development() -> bool:
    """
    開発版かどうか判定する関数
    Nuitka/Pyinstallerでコンパイルされていない場合は開発環境とする。
    """
    # nuitkaビルドをした際はグローバルに__compiled__が含まれる
    if "__compiled__" in globals():
        return False

    # pyinstallerでビルドをした際はsys.frozenが設定される
    elif getattr(sys, "frozen", False):
        return False

    return True


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
