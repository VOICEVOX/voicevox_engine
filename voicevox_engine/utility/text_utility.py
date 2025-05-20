"""テキスト処理に関するユーティリティ"""

from re import findall
from typing import Final

_HANKAKU_CHARS: Final = "".join(chr(0x21 + i) for i in range(94))
_ZENKAKU_CHARS: Final = "".join(chr(0xFF01 + i) for i in range(94))

_HANKAKU_TO_ZENKAKU_TABLE: Final = str.maketrans(_HANKAKU_CHARS, _ZENKAKU_CHARS)
_ZENKAKU_TO_HANKAKU_TABLE: Final = str.maketrans(_ZENKAKU_CHARS, _HANKAKU_CHARS)


def replace_hankaku_alphabets_with_zenkaku(string: str) -> str:
    """文字列に含まれる半角アルファベットを全角アルファベットで置き換える。"""
    return string.translate(_HANKAKU_TO_ZENKAKU_TABLE)


def replace_zenkaku_alphabets_with_hankaku(string: str) -> str:
    """文字列に含まれる全角アルファベットを半角アルファベットで置き換える。"""
    return string.translate(_ZENKAKU_TO_HANKAKU_TABLE)


def count_mora(string: str) -> int:
    """文字列に含まれるモーラを数える。"""
    # 複数のカタカナが1つのモーラを構成するパターン
    rule_others = "[イ][ェ]|[ヴ][ャュョ]|[ウクグトド][ゥ]|[テデ][ィェャュョ]|[クグ][ヮ]"
    rule_line_i = "[キシチニヒミリギジヂビピ][ェャュョ]|[キニヒミリギビピ][ィ]"
    rule_line_u = "[クツフヴグ][ァ]|[ウクスツフヴグズ][ィ]|[ウクツフヴグ][ェォ]"
    # 1つのカタカナが1つのモーラを構成するパターン
    rule_one_mora = "[ァ-ヴー]"

    pattern = f"(?:{rule_others}|{rule_line_i}|{rule_line_u}|{rule_one_mora})"

    return len(findall(pattern, string))
