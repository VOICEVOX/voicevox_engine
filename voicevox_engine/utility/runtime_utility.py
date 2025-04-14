"""実行環境に関する utility"""

import sys


def is_development() -> bool:
    """
    動作環境が開発版であるか否かを返す。
    Pyinstallerでコンパイルされていない場合は開発環境とする。
    """
    # pyinstallerでビルドをした際はsys.frozenが設定される
    return False if getattr(sys, "frozen", False) else True
