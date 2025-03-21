"""英単語をカタカナ読みにする処理"""

import re

import e2k

from .njd_feature_processor import NJDFeature


def _convert_zenkaku_alphabet_to_hankaku(surface: str) -> str:
    return surface.translate(
        str.maketrans(
            "".join(chr(0xFF01 + i) for i in range(94)),
            "".join(chr(0x21 + i) for i in range(94)),
        )
    )


_global_c2k: e2k.C2K | None = None


def _initialize_c2k() -> e2k.C2K:
    global _global_c2k
    if _global_c2k is None:
        _global_c2k = e2k.C2K()

    return _global_c2k


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


def convert_english_in_njd_features_to_katakana(
    njd_features: list[NJDFeature],
) -> list[NJDFeature]:
    """e2kを用いて、NJD Features内の読みが不明な英単語をカタカナに変換する"""
    for i, feature in enumerate(njd_features):
        # Mecabの解析で未知語となった場合、読みは空となる
        # NJDは、読みが空の場合、読みを補完して品詞をフィラーとして扱う
        if feature.pos != "フィラー" or feature.chain_rule != "*":
            continue

        c2k = _initialize_c2k()

        # OpenJTalkはアルファベットを全角に変換するので、半角に戻す
        hankaku_string = _convert_zenkaku_alphabet_to_hankaku(feature.string)

        # アルファベット以外の文字が含まれている場合や、全て大文字の場合は、e2kでの解析を行わない
        if not re.fullmatch("[a-zA-Z]+", hankaku_string) or re.fullmatch(
            "[A-Z]+", hankaku_string
        ):
            continue

        kana = ""
        # キャメルケース的な単語に対応させるため、大文字で分割する
        for word in re.findall("[a-zA-Z][a-z]*", hankaku_string):
            # 大文字のみ、もしくは短いワードの場合は、e2kでの解析を行わない
            if word == word.upper() or len(word) < 3:
                for alphabet in word:
                    kana += ojt_alphabet_kana_mapping[alphabet.upper()]
            else:
                kana += c2k(word.lower())

        njd_features[i] = NJDFeature.from_english_kana(feature.string, kana)

    return njd_features
