"""NJD Featureの処理"""

import re
from dataclasses import asdict, dataclass

import pyopenjtalk


@dataclass
class NJDFeature:
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
    def from_english_kana(cls, english: str, kana: str) -> "NJDFeature":
        """英語のカタカナ読みからNJDFeatureを作成する"""
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

    njd_features = list(map(lambda f: NJDFeature(**f), pyopenjtalk.run_frontend(text)))

    if enable_e2k:
        # FIXME: トップレベルでimportすると循環importになるため、関数内で遅延importする形になっている
        from .katakana_english import convert_english_in_njd_features_to_katakana

        convert_english_in_njd_features_to_katakana(njd_features)

    return pyopenjtalk.make_label(list(map(asdict, njd_features)))  # type: ignore
