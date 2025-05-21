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


def should_convert_english_to_katakana(string: HankakuAlphabet) -> bool:
    """読みが不明な英単語をカタカナに変換するべきか否かを判定する"""
    if len(string) < 3:
        return False

    # 全て大文字の場合は、e2kでの解析を行わない
    if string == string.upper():
        return False

    return True


def convert_english_to_katakana(string: HankakuAlphabet) -> str:
    """kanalizerを用いて、読みが不明な英単語をカタカナに変換する"""
    kana = ""
    # キャメルケース的な単語に対応させるため、大文字で分割する
    for word in re.findall("[a-zA-Z][a-z]*", string):
        word = HankakuAlphabet(word)

        # 大文字のみ、もしくは短いワードの場合は、kanalizerでの変換を行わない
        if not should_convert_english_to_katakana(word):
            for alphabet in word:
                kana += ojt_alphabet_kana_mapping[alphabet.upper()]
        else:
            kana += kanalizer.convert(word.lower())

    return kana
