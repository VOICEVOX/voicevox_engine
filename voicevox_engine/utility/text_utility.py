"""テキスト処理に関するユーティリティ"""

from typing import Final

HANKAKU_CHARACTERS: Final = "".join(chr(0x21 + i) for i in range(94))
ZENKAKU_CHARACTERS: Final = "".join(chr(0xFF01 + i) for i in range(94))

HANKAKU_TO_ZENKAKU_TABLE: Final = str.maketrans(HANKAKU_CHARACTERS, ZENKAKU_CHARACTERS)
ZENKAKU_TO_HANKAKU_TABLE: Final = str.maketrans(ZENKAKU_CHARACTERS, HANKAKU_CHARACTERS)


def replace_hankaku_alphabets_with_zenkaku(string: str) -> str:
    """文字列に含まれる半角アルファベットを全角アルファベットで置き換える。"""
    return string.translate(HANKAKU_TO_ZENKAKU_TABLE)


def replace_zenkaku_alphabets_with_hankaku(string: str) -> str:
    """文字列に含まれる全角アルファベットを半角アルファベットで置き換える。"""
    return string.translate(ZENKAKU_TO_HANKAKU_TABLE)
