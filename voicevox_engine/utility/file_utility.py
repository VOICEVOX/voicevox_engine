"""ファイル操作に関するユーティリティ"""

import os
import traceback


def delete_file(file_path: str) -> None:
    """指定されたファイルを削除する。"""
    try:
        os.remove(file_path)
    except OSError:
        traceback.print_exc()
