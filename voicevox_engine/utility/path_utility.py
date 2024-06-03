"""パスに関する utility"""

import sys
from pathlib import Path

from platformdirs import user_data_dir


def engine_root() -> Path:
    """エンジンのルートディレクトリを指すパスを取得する。"""
    if _is_development():
        # git レポジトリのルートを指している
        root_dir = Path(__file__).parents[2]
    else:
        root_dir = Path(sys.argv[0]).parent

    return root_dir.resolve(strict=True)


def resource_root() -> Path:
    """リソースのルートディレクトリを指すパスを取得する。"""
    return engine_root() / "resources"


def engine_manifest_path() -> Path:
    """エンジンマニフェストのパスを取得する。"""
    # NOTE: VOICEVOX API の規定によりエンジンマニフェストファイルは必ず `<engine_root>/engine_manifest.json` に存在する
    return engine_root() / "engine_manifest.json"


def _is_development() -> bool:
    """
    動作環境が開発版であるか否かを返す。
    Pyinstallerでコンパイルされていない場合は開発環境とする。
    """
    # pyinstallerでビルドをした際はsys.frozenが設定される
    return False if getattr(sys, "frozen", False) else True


def get_save_dir() -> Path:
    """ファイルの保存先ディレクトリを指すパスを取得する。"""

    # FIXME: ファイル保存場所をエンジン固有のIDが入ったものにする
    # FIXME: Windowsは`voicevox-engine/voicevox-engine`ディレクトリに保存されているので
    # `VOICEVOX/voicevox-engine`に変更する
    if _is_development():
        app_name = "voicevox-engine-dev"
    else:
        app_name = "voicevox-engine"
    return Path(user_data_dir(app_name))
