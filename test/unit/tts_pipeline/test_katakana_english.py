from voicevox_engine.tts_pipeline.katakana_english import extract_fullcontext_with_e2k
from voicevox_engine.tts_pipeline.text_analyzer import Label


def test_extract_fullcontext_with_e2k_normal() -> None:
    """`extract_fullcontext_with_e2k`は英単語をアルファベットそのままで読まない"""
    phonemes = [
        Label.from_feature(feature).phoneme
        for feature in extract_fullcontext_with_e2k("Voivo")
    ]

    expected_phonemes = [
        "sil",
        "b",
        "o",
        "i",
        "b",
        "o",
        "sil",
    ]

    # FIXME: e2kの結果が決定論的でない場合、テストが落ちる可能性がある
    assert expected_phonemes == phonemes


def test_extract_fullcontext_with_e2k_uppercase() -> None:
    """`extract_fullcontext_with_e2k`は大文字のみの英単語をアルファベットそのままで読む"""
    phonemes = [
        Label.from_feature(feature).phoneme
        for feature in extract_fullcontext_with_e2k("VOIVO")
    ]

    expected_phonemes = [
        "sil",
        "b",
        "u",
        "i",
        "o",
        "o",
        "a",
        "i",
        "b",
        "u",
        "i",
        "o",
        "o",
        "sil",
    ]

    assert expected_phonemes == phonemes


def test_extract_fullcontext_with_e2k_short() -> None:
    """`extract_fullcontext_with_e2k`は2文字以下の英単語をアルファベットそのままで読む"""
    phonemes = [
        Label.from_feature(feature).phoneme
        for feature in extract_fullcontext_with_e2k("Vo")
    ]

    expected_phonemes = ["sil", "b", "u", "i", "o", "o", "sil"]

    assert expected_phonemes == phonemes
