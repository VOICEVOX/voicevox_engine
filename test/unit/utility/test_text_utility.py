"""テキスト処理用ユーティリティのテスト"""

import pytest

from voicevox_engine.tts_pipeline.kana_converter import parse_kana
from voicevox_engine.utility.text_utility import (
    count_mora,
    replace_hankaku_alphabets_with_zenkaku,
    replace_zenkaku_alphabets_with_hankaku,
)


@pytest.mark.parametrize(
    ("text", "true_replaced_text"),
    [
        ("あいうえお", "あいうえお"),
        ("ABCDE", "ＡＢＣＤＥ"),
        ("ABCＤＥあいうえお", "ＡＢＣＤＥあいうえお"),
    ],
)
def test_replace_hankaku_alphabets_with_zenkaku_only_hiragana(
    text: str, true_replaced_text: str
) -> None:
    """`replace_hankaku_alphabets_with_zenkaku()` は文字列中の半角アルファベットのみを置き換える。"""
    # Outputs
    replaced_text = replace_hankaku_alphabets_with_zenkaku(text)
    # Tests
    assert true_replaced_text == replaced_text


@pytest.mark.parametrize(
    ("text", "true_replaced_text"),
    [
        ("あいうえお", "あいうえお"),
        ("ＡＢＣＤＥ", "ABCDE"),
        ("ABCＤＥあいうえお", "ABCDEあいうえお"),
    ],
)
def test_replace_zenkaku_alphabets_with_hankaku_only_hiragana(
    text: str, true_replaced_text: str
) -> None:
    """`replace_zenkaku_alphabets_with_hankaku()` は文字列中の全角アルファベットのみを置き換える。"""
    # Outputs
    replaced_text = replace_zenkaku_alphabets_with_hankaku(text)
    # Tests
    assert true_replaced_text == replaced_text


@pytest.mark.parametrize(
    ("text", "true_n_mora"),
    [
        ("エ", 1),
        ("アサ", 2),
        ("イェーガー", 4),
        ("クヮンセイ", 4),
    ],
)
def test_count_mora(text: str, true_n_mora: int) -> None:
    """`count_mora()` は文字列に含まれるモーラ数をカウントする。"""
    # Outputs
    n_mora = count_mora(text)
    # Tests
    assert true_n_mora == n_mora


def test_count_mora_small_char() -> None:
    """`count_mora()` は小文字が大文字と一体かを判断してモーラ数をカウントする。"""
    smalls = ["ァ", "ィ", "ゥ", "ェ", "ォ", "ッ", "ャ", "ュ", "ョ", "ヮ"]
    bigs = filter(lambda c: c not in smalls, [chr(i) for i in range(12449, 12533)])
    for big in bigs:
        for small in "ァィゥェォャュョ":
            # Inputs
            text = f"{big}{small}"
            # Outputs
            n_mora = count_mora(text)
            # Expects
            # NOTE: `parse_kana()` によるモーラ化の結果と一致するか検証している
            true_n_mora = sum(map(lambda ap: len(ap.moras), parse_kana(text + "'")))

            # tests
            assert true_n_mora == n_mora
