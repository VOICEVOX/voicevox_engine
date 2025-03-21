from voicevox_engine.tts_pipeline.katakana_english import (
    convert_english_in_njd_features_to_katakana,
)
from voicevox_engine.tts_pipeline.njd_feature_processor import NJDFeature


def test_convert_english_in_njd_features_to_katakana_normal() -> None:
    """`convert_english_in_njd_features_to_katakana`は英単語をアルファベットそのままで読まない"""
    features = [
        NJDFeature(
            string="Ｖｏｉｖｏ",
            pos="フィラー",
            pos_group1="*",
            pos_group2="*",
            pos_group3="*",
            ctype="*",
            cform="*",
            orig="Ｖｏｉｖｏ",
            read="ブイオーアイブイオー",
            pron="ブイオーアイブイオー",
            acc=0,
            mora_size=10,
            chain_rule="*",
            chain_flag=-1,
        ),
    ]
    prons = [
        feature.pron
        for feature in convert_english_in_njd_features_to_katakana(features)
    ]

    expected_prons = ["ボイボ"]

    # FIXME: e2kの結果が決定論的でない場合、テストが落ちる可能性がある
    assert expected_prons == prons


def test_convert_english_in_njd_features_to_katakana_uppercase() -> None:
    """`convert_english_in_njd_features_to_katakana`は大文字のみの英単語をアルファベットそのままで読む"""
    features = [
        NJDFeature(
            string="ＶＯＩＶＯ",
            pos="フィラー",
            pos_group1="*",
            pos_group2="*",
            pos_group3="*",
            ctype="*",
            cform="*",
            orig="ＶＯＩＶＯ",
            read="ブイオーアイブイオー",
            pron="ブイオーアイブイオー",
            acc=0,
            mora_size=10,
            chain_rule="*",
            chain_flag=-1,
        ),
    ]
    prons = [
        feature.pron
        for feature in convert_english_in_njd_features_to_katakana(features)
    ]

    expected_prons = ["ブイオーアイブイオー"]

    assert expected_prons == prons


def test_convert_english_in_njd_features_to_katakana_short() -> None:
    """`convert_english_in_njd_features_to_katakana`は2文字以下の英単語をアルファベットそのままで読む"""
    # NOTE: 実際の pyopenjtalk.run_frontend の出力とは異なる
    features = [
        NJDFeature(
            string="Ｖｏ",
            pos="フィラー",
            pos_group1="*",
            pos_group2="*",
            pos_group3="*",
            ctype="*",
            cform="*",
            orig="Ｖｏ",
            read="ブイオー",
            pron="ブイオー",
            acc=0,
            mora_size=4,
            chain_rule="*",
            chain_flag=-1,
        ),
    ]
    prons = [
        feature.pron
        for feature in convert_english_in_njd_features_to_katakana(features)
    ]

    expected_prons = ["ブイオー"]

    assert expected_prons == prons
