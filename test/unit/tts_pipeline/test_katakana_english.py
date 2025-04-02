from voicevox_engine.tts_pipeline.katakana_english import (
    convert_english_to_katakana,
    should_convert_english_to_katakana,
)
from voicevox_engine.utility.character_width_utility import is_hankaku_alphabet


def test_should_convert_english_to_katakana_normal() -> None:
    """`should_convert_english_to_katakana`は英単語を変換すべきであると判定する"""
    string = "Voivo"
    assert is_hankaku_alphabet(string)

    is_should_convert = should_convert_english_to_katakana(string)

    assert is_should_convert


def test_should_convert_english_to_katakana_uppercase() -> None:
    """`should_convert_english_to_katakana`は大文字のみの英単語を変換すべきではないと判定する"""
    string = "VOIVO"
    assert is_hankaku_alphabet(string)

    is_should_convert = should_convert_english_to_katakana(string)

    assert not is_should_convert


def test_should_convert_english_to_katakana_short() -> None:
    """`should_convert_english_to_katakana`は2文字以下の英単語を変換すべきではないと判定する"""
    string = "Vo"
    assert is_hankaku_alphabet(string)

    is_should_convert = should_convert_english_to_katakana(string)

    assert not is_should_convert


def test_convert_english_to_katakana() -> None:
    """`convert_english_to_katakana`は英単語をアルファベットそのままで読まない"""
    string = "Voivo"
    assert is_hankaku_alphabet(string)

    pron = convert_english_to_katakana(string)

    expected_pron = "ボイボ"

    assert expected_pron == pron
