"""テキスト処理に関するユーティリティ"""

import re
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


# 複数のカタカナが1つのモーラを構成するパターン
_RULE_OTHERS: Final = (
    "[イ][ェ]|[ヴ][ャュョ]|[ウクグトド][ゥ]|[テデ][ィェャュョ]|[クグ][ヮ]"
)
_RULE_LINE_I: Final = "[キシチニヒミリギジヂビピ][ェャュョ]|[キニヒミリギビピ][ィ]"
_RULE_LINE_U: Final = "[クツフヴグ][ァ]|[ウクスツフヴグズ][ィ]|[ウクツフヴグ][ェォ]"
# 1つのカタカナが1つのモーラを構成するパターン
_RULE_ONE_MORA: Final = "[ァ-ヴー]"

_MORA_PATTERN: Final = re.compile(
    f"(?:{_RULE_OTHERS}|{_RULE_LINE_I}|{_RULE_LINE_U}|{_RULE_ONE_MORA})"
)


def count_mora(string: str) -> int:
    """文字列に含まれるモーラを数える。"""
    return len(_MORA_PATTERN.findall(string))
