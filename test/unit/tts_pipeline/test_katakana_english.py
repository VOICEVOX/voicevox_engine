"""英単語のカタカナ変換機能の単体テスト。"""

import pytest

from voicevox_engine.tts_pipeline.katakana_english import (
    HankakuAlphabet,
    _convert_as_char_wise_katakana,
    _should_convert_english_to_katakana,
    _split_into_words,
    convert_english_to_katakana,
    is_hankaku_alphabet,
)


@pytest.mark.parametrize(
    ("string", "true_words"),
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


@pytest.mark.parametrize(
    ("string", "true_should"),
    [
        ("voivo", True),
        ("Voivo", True),
        ("VOIVO", False),  # 大文字のみの英単語は変換すべきではない
        ("V", False),  # 1文字の英単語は変換すべきではない
    ],
)
def test_should_convert_english_to_katakana(string: str, true_should: bool) -> None:
    # outputs
    should = _should_convert_english_to_katakana(HankakuAlphabet(string))
    # tests
    assert true_should == should


@pytest.mark.parametrize(
    ("alphabets", "true_yomi"),
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
