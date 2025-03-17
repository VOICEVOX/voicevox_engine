"""アルファベット読み上げ処理"""

import re
from typing import Any

import e2k
import pyopenjtalk


def _convert_zenkaku_alphabet_to_hankaku(surface: str) -> str:
    return surface.translate(
        str.maketrans(
            "".join(chr(0xFF01 + i) for i in range(94)),
            "".join(chr(0x21 + i) for i in range(94)),
        )
    )


c2k: e2k.C2K | None = None

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


def extract_fullcontext_with_e2k(text: str) -> list[str]:
    """e2kを用いて読みが不明な英単語をカタカナに変換し、フルコンテキストラベルを生成する"""
    global c2k
    njd_features: list[dict[str, Any]] = pyopenjtalk.run_frontend(text)
    for i, feature in enumerate(njd_features):
        # Mecabの解析で未知語となった場合、読みは空となる
        # NJDは、読みが空の場合、読みを補完して品詞をフィラーとして扱う
        if feature["pos"] != "フィラー" or feature["chain_rule"] != "*":
            continue

        if c2k is None:
            c2k = e2k.C2K()

        # OpenJTalkはアルファベットを全角に変換するので、半角に戻す
        hankaku_string = _convert_zenkaku_alphabet_to_hankaku(feature["string"])

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

        # TODO: user_dict/model.py内の処理と重複しているため、リファクタリングする
        rule_others = (
            "[イ][ェ]|[ヴ][ャュョ]|[ウクグトド][ゥ]|[テデ][ィェャュョ]|[クグ][ヮ]"
        )
        rule_line_i = "[キシチニヒミリギジヂビピ][ェャュョ]|[キニヒミリギビピ][ィ]"
        rule_line_u = "[クツフヴグ][ァ]|[ウクスツフヴグズ][ィ]|[ウクツフヴグ][ェォ]"
        rule_one_mora = "[ァ-ヴー]"

        njd_features[i] = {
            "string": kana,
            "pos": "名詞",
            "pos_group1": "固有名詞",
            "pos_group2": "一般",
            "pos_group3": "*",
            "ctype": "*",
            "cform": "*",
            "orig": feature["string"],
            "read": kana,
            "pron": kana,
            "acc": 1,
            "mora_size": len(
                re.findall(
                    f"(?:{rule_others}|{rule_line_i}|{rule_line_u}|{rule_one_mora})",
                    kana,
                )
            ),
            "chain_rule": "*",
            "chain_flag": -1,
        }

    return pyopenjtalk.make_label(njd_features)  # type: ignore
