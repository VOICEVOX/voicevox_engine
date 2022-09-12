import os
import sys
import traceback
from pathlib import Path

from appdirs import user_data_dir


def engine_root() -> Path:
    # nuitkaビルドをした際はグローバルに__compiled__が含まれる
    if "__compiled__" in globals():
        root_dir = Path(sys.argv[0]).parent

    # pyinstallerでビルドをした際はsys.frozenが設定される
    elif getattr(sys, "frozen", False):
        root_dir = Path(sys.argv[0]).parent

    else:
        root_dir = Path(__file__).parents[2]

    return root_dir.resolve(strict=True)


def get_save_dir():
    # FIXME: ファイル保存場所をエンジン固有のIDが入ったものにする
    # FIXME: Windowsは`voicevox-engine/voicevox-engine`ディレクトリに保存されているので
    # `VOICEVOX/voicevox-engine`に変更する
    return Path(user_data_dir("voicevox-engine"))


def delete_file(file_path: str) -> None:
    try:
        os.remove(file_path)
    except OSError:
        traceback.print_exc()
