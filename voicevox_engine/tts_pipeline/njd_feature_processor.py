"""NJD Featureの処理"""

import re
from dataclasses import asdict, dataclass

import pyopenjtalk

from .katakana_english import (
    convert_english_to_katakana,
    convert_zenkaku_alphabet_to_hankaku,
    is_hankaku_alphabet,
    should_convert_english_to_katakana,
)


@dataclass
class NjdFeature:
    """NJDのFeature"""

    string: str
    pos: str
    pos_group1: str
    pos_group2: str
    pos_group3: str
    ctype: str
    cform: str
    orig: str
    read: str
    pron: str
    acc: int
    mora_size: int
    chain_rule: str
    chain_flag: int

    @classmethod
    def from_english_kana(cls, english: str, kana: str) -> "NjdFeature":
        """英語のカタカナ読みからNjdFeatureを作成する"""
        # TODO: user_dict/model.py内の処理と重複しているため、リファクタリングする
        rule_others = (
            "[イ][ェ]|[ヴ][ャュョ]|[ウクグトド][ゥ]|[テデ][ィェャュョ]|[クグ][ヮ]"
        )
        rule_line_i = "[キシチニヒミリギジヂビピ][ェャュョ]|[キニヒミリギビピ][ィ]"
        rule_line_u = "[クツフヴグ][ァ]|[ウクスツフヴグズ][ィ]|[ウクツフヴグ][ェォ]"
        rule_one_mora = "[ァ-ヴー]"
        mora_size = len(
            re.findall(
                f"(?:{rule_others}|{rule_line_i}|{rule_line_u}|{rule_one_mora})", kana
            )
        )
        return cls(
            string=kana,
            pos="名詞",
            pos_group1="固有名詞",
            pos_group2="一般",
            pos_group3="*",
            ctype="*",
            cform="*",
            orig=english,
            read=kana,
            pron=kana,
            acc=1,
            mora_size=mora_size,
            chain_rule="*",
            chain_flag=-1,
        )


def _is_unknown_reading_word(feature: NjdFeature) -> bool:
    """読みが不明な単語であるか否かを判定する"""
    # Mecabの解析で未知語となった場合、読みは空となる
    # NJDは、読みが空の場合、読みを補完して品詞をフィラーとして扱う
    return feature.pos == "フィラー" and feature.chain_rule == "*"


def text_to_full_context_labels(text: str, enable_e2k: bool) -> list[str]:
    """日本語文からフルコンテキストラベルを生成する"""
    # TODO: この関数のテストについて検討する
    # https://github.com/VOICEVOX/voicevox_engine/pull/1562/files#r2014009618
    if len(text.strip()) == 0:
        return []

    njd_features = list(map(lambda f: NjdFeature(**f), pyopenjtalk.run_frontend(text)))

    if enable_e2k:
        for i, feature in enumerate(njd_features):
            if not _is_unknown_reading_word(feature):
                continue
            hankaku_string = convert_zenkaku_alphabet_to_hankaku(feature.string)
            if not is_hankaku_alphabet(hankaku_string):
                continue
            if not should_convert_english_to_katakana(hankaku_string):
                continue
            new_pron = convert_english_to_katakana(hankaku_string)
            njd_features[i] = NjdFeature.from_english_kana(
                feature.string,
                new_pron,
            )

    return pyopenjtalk.make_label(list(map(asdict, njd_features)))  # type: ignore
