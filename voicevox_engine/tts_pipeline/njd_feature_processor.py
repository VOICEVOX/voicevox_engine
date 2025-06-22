"""NJD Featureの処理"""

from dataclasses import asdict, dataclass

import pyopenjtalk

from ..utility.text_utility import count_mora, replace_zenkaku_alphabets_with_hankaku
from .katakana_english import convert_english_to_katakana, is_hankaku_alphabet


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
        return cls(
            string=english,
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
            mora_size=count_mora(kana),
            chain_rule="*",
            chain_flag=-1,
        )


def _is_unknown_reading_word(feature: NjdFeature) -> bool:
    """読みが不明な単語であるか否かを判定する。"""
    # NOTE: Mecabは未知語の読みを空とし、NJDは空の読みを補完して品詞をフィラーとして扱う
    return feature.pos == "フィラー" and feature.chain_rule == "*"


def _is_pau_space(feature: NjdFeature) -> bool:
    """pauとして扱われる全角スペースか否かを判定する"""
    return feature.string == "　" and feature.pron == "、"


def _is_between_alphabet(features: list[NjdFeature], index: int) -> bool:
    """指定されたインデックスのfeatureがアルファベットのfeatureに挟まれているか判定する"""
    if index <= 0 or index >= len(features) - 1:
        return False

    prev_feature = features[index - 1]
    next_feature = features[index + 1]

    prev_is_alphabet = is_hankaku_alphabet(
        replace_zenkaku_alphabets_with_hankaku(prev_feature.string)
    )
    next_is_alphabet = is_hankaku_alphabet(
        replace_zenkaku_alphabets_with_hankaku(next_feature.string)
    )

    return prev_is_alphabet and next_is_alphabet


def _remove_pau_space_between_alphabet(features: list[NjdFeature]) -> list[NjdFeature]:
    """アルファベットのfeatureに挟まれている、pauとして扱われる全角スペースを削除した、featuresのコピーを返す"""
    return [
        feature
        for i, feature in enumerate(features)
        if not (_is_pau_space(feature) and _is_between_alphabet(features, i))
    ]


def text_to_full_context_labels(text: str, enable_katakana_english: bool) -> list[str]:
    """日本語文からフルコンテキストラベルを生成する"""
    # TODO: この関数のテストについて検討する
    # https://github.com/VOICEVOX/voicevox_engine/pull/1562/files#r2014009618
    if len(text.strip()) == 0:
        return []

    njd_features = list(map(lambda f: NjdFeature(**f), pyopenjtalk.run_frontend(text)))

    if enable_katakana_english:
        for i, feature in enumerate(njd_features):
            string = replace_zenkaku_alphabets_with_hankaku(feature.string)
            if _is_unknown_reading_word(feature) and is_hankaku_alphabet(string):
                new_pron = convert_english_to_katakana(string)
                njd_features[i] = NjdFeature.from_english_kana(feature.string, new_pron)

        # 英単語間のスペースがpauとして扱われて読みが不自然になるため、削除する
        njd_features = _remove_pau_space_between_alphabet(njd_features)

    return pyopenjtalk.make_label(list(map(asdict, njd_features)))  # type: ignore
