"""英単語のカタカナ変換機能の単体テスト。"""

import pytest

from voicevox_engine.tts_pipeline.katakana_english import (
    HankakuAlphabet,
    _convert_as_char_wise_katakana,
    _split_into_words,
    convert_english_to_katakana,
    is_hankaku_alphabet,
    should_convert_english_to_katakana,
)


@pytest.mark.parametrize(
    "string,true_words",
    [
        ("voicevox", ["voicevox"]),
        ("VoiceVox", ["Voice", "Vox"]),
        ("VoiceVOX", ["Voice", "V", "O", "X"]),
        ("VOICEVOX", ["V", "O", "I", "C", "E", "V", "O", "X"]),
    ],
)
def test_split_into_words(string: str, true_words: list[str]) -> None:
    """`_split_into_words()` はアルファベット列を単語列へ分割する。"""
    # outputs
    words = _split_into_words(HankakuAlphabet(string))
    # expects
    true_words_typed = list(map(HankakuAlphabet, true_words))
    # tests
    assert true_words_typed == words


def test_should_convert_english_to_katakana_normal() -> None:
    """`should_convert_english_to_katakana`は英単語を変換すべきであると判定する"""
    string = "Voivo"
    assert is_hankaku_alphabet(string)

    should_convert = should_convert_english_to_katakana(string)

    assert should_convert


def test_should_convert_english_to_katakana_uppercase() -> None:
    """`should_convert_english_to_katakana`は大文字のみの英単語を変換すべきではないと判定する"""
    string = "VOIVO"
    assert is_hankaku_alphabet(string)

    should_convert = should_convert_english_to_katakana(string)

    assert not should_convert


def test_should_convert_english_to_katakana_short() -> None:
    """`should_convert_english_to_katakana`は2文字以下の英単語を変換すべきではないと判定する"""
    string = "Vo"
    assert is_hankaku_alphabet(string)

    should_convert = should_convert_english_to_katakana(string)

    assert not should_convert


@pytest.mark.parametrize(
    "alphabets,true_yomi",
    [
        ("aa", "エーエー"),
        ("Aa", "エーエー"),
        ("aA", "エーエー"),
        ("AA", "エーエー"),
        ("VOICE", "ブイオーアイシーイー"),
    ],
)
def test_convert_as_char_wise_katakana(alphabets: str, true_yomi: str) -> None:
    """`_convert_as_char_wise_katakana()` はアルファベット列を文字ごとにカタカナ読みする。"""
    # outputs
    yomi = _convert_as_char_wise_katakana(HankakuAlphabet(alphabets))
    # tests
    assert true_yomi == yomi


def test_convert_english_to_katakana() -> None:
    """`convert_english_to_katakana`は英単語をアルファベットそのままで読まない"""
    string = "Voivo"
    assert is_hankaku_alphabet(string)

    pron = convert_english_to_katakana(string)

    expected_pron = "ヴォイヴォ"

    assert expected_pron == pron
