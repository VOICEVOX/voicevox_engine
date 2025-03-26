"""NJD Featureの処理"""

import re
from dataclasses import asdict, dataclass

import pyopenjtalk

from .katakana_english import convert_english_to_katakana, is_convertible_to_katakana


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


def text_to_full_context_labels(text: str, enable_e2k: bool) -> list[str]:
    """日本語文からフルコンテキストラベルを生成する"""
    if len(text.strip()) == 0:
        return []

    njd_features = list(map(lambda f: NjdFeature(**f), pyopenjtalk.run_frontend(text)))

    if enable_e2k:
        for i, feature in enumerate(njd_features):
            if is_convertible_to_katakana(
                feature.pos, feature.chain_rule, feature.string
            ):
                new_pron = convert_english_to_katakana(feature.string)
                njd_features[i] = NjdFeature.from_english_kana(
                    feature.string,
                    new_pron,
                )

    return pyopenjtalk.make_label(list(map(asdict, njd_features)))  # type: ignore
