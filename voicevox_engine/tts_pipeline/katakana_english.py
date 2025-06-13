"""英単語をカタカナ読みにする処理"""

import re
from typing import NewType, TypeGuard

import kanalizer

# 半角アルファベット文字列を示す型
HankakuAlphabet = NewType("HankakuAlphabet", str)


# OpenJTalkで使っているアルファベット→カタカナの対応表
# https://github.com/VOICEVOX/open_jtalk/blob/b9b1bf6a0cba6bc9550b4521913b20334a218dfc/src/njd_set_pronunciation/njd_set_pronunciation_rule_utf_8.h#L397
ojt_alphabet_kana_mapping = {
    "A": "エー",
    "B": "ビー",
    "C": "シー",
    "D": "ディー",
    "E": "イー",
    "F": "エフ",
    "G": "ジー",
    "H": "エイチ",
    "I": "アイ",
    "J": "ジェー",
    "K": "ケー",
    "L": "エル",
    "M": "エム",
    "N": "エヌ",
    "O": "オー",
    "P": "ピー",
    "Q": "キュー",
    "R": "アール",
    "S": "エス",
    "T": "ティー",
    "U": "ユー",
    "V": "ブイ",
    "W": "ダブリュー",
    "X": "エックス",
    "Y": "ワイ",
    "Z": "ズィー",
}


def is_hankaku_alphabet(text: str) -> TypeGuard[HankakuAlphabet]:
    """文字列が半角アルファベットのみで構成されているかを判定する"""
    return bool(re.fullmatch("[a-zA-Z]+", text))


def _split_into_words(string: HankakuAlphabet) -> list[HankakuAlphabet]:
    """
    アルファベット列を単語列へ分割する。

    Examples
    --------
    >>> _split_into_words("VoiceVox")
    ["Voice", "Vox"]
    """
    # TODO: 「全て大文字で書かれた英単語は、バラバラの文字へ分割される」という動作がユーザーにとって最適か検討 (ref: https://github.com/VOICEVOX/voicevox_engine/issues/1524#issuecomment-2849254324)
    # NOTE: キャメルケース的な単語に対応させるため、大文字で分割する
    return list(map(HankakuAlphabet, re.findall("[a-zA-Z][a-z]*", string)))


def _should_convert_english_to_katakana(string: HankakuAlphabet) -> bool:
    """読みが不明な英単語をカタカナに変換するべきか否かを判定する。"""
    # 1文字の場合は変換しない
    if len(string) == 1:
        return False

    # 全て大文字の場合はカタカナへ変換しない
    if string == string.upper():
        return False

    return True


def _convert_as_char_wise_katakana(alphabets: HankakuAlphabet) -> str:
    """
    アルファベット列を文字ごとのカタカナ読みへ変換する。

    Examples
    --------
    >>> _convert_as_char_wise_katakana("VOICE")
    "ブイオーアイシーイー"
    """
    yomi = ""
    for alphabet in alphabets:
        yomi += ojt_alphabet_kana_mapping[alphabet.upper()]
    return yomi


def convert_english_to_katakana(string: HankakuAlphabet) -> str:
    """英単語をカタカナ読みに変換する。"""
    kana = ""
    for word in _split_into_words(string):
        if _should_convert_english_to_katakana(word):
            # 単語を英単語とみなして読みを生成する
            kana += kanalizer.convert(word.lower())
        else:
            kana += _convert_as_char_wise_katakana(word)
    return kana
