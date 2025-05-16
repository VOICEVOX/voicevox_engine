"""テキスト処理用ユーティリティのテスト"""

import pytest

from voicevox_engine.utility.text_utility import (
    replace_hankaku_alphabets_with_zenkaku,
    replace_zenkaku_alphabets_with_hankaku,
)


@pytest.mark.parametrize(
    "text,true_replaced_text",
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
    "text,true_replaced_text",
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
