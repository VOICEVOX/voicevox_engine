"""ファイル操作に関するユーティリティ"""

import os
import traceback


def try_delete_file(file_path: str) -> None:
    """指定されたファイルの削除を試み、失敗したらログを残したうえでエラーを握り潰す。"""
    try:
        os.remove(file_path)
    except OSError:
        traceback.print_exc()
