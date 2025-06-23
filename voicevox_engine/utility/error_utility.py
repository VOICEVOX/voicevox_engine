"""エラーに関するユーティリティ。"""


class UnreachableError(Exception):
    """本来は実行されないパスが実行された。"""
