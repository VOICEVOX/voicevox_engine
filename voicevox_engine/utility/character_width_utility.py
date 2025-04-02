"""文字列の全角・半角に関する utility"""

import re
from typing import NewType, TypeGuard

# 半角アルファベット文字列を示す型
HankakuAlphabet = NewType("HankakuAlphabet", str)


def is_hankaku_alphabet(text: str) -> TypeGuard[HankakuAlphabet]:
    """文字列が半角アルファベットのみで構成されているかを判定する"""
    return bool(re.fullmatch("[a-zA-Z]+", text))


def convert_zenkaku_alphabet_to_hankaku(text: str) -> str:
    """全角アルファベットを半角に変換する"""
    return text.translate(
        str.maketrans(
            "".join(chr(0xFF01 + i) for i in range(94)),
            "".join(chr(0x21 + i) for i in range(94)),
        )
    )
