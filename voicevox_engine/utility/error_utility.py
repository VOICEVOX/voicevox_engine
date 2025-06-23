"""エラーに関するユーティリティ。"""


class NeverError(Exception):
    """本来は実行されないパスが実行された。"""
