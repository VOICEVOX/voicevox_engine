from voicevox_engine.tts_pipeline.katakana_english import (
    convert_english_to_katakana,
    is_convertible_to_katakana,
)


def test_is_convertible_to_katakana_normal() -> None:
    """`is_convertible_to_katakana`は英単語を変換可能であると判定する"""
    is_convertible = is_convertible_to_katakana(
        pos="フィラー", chain_rule="*", string="Ｖｏｉｖｏ"
    )

    assert is_convertible


def test_is_convertible_to_katakana_uppercase() -> None:
    """`is_convertible_to_katakana`は大文字のみの英単語を変換可能ではないと判定する"""
    is_convertible = is_convertible_to_katakana(
        pos="フィラー",
        chain_rule="*",
        string="ＶＯＩＶＯ",
    )

    assert not is_convertible


def test_is_convertible_to_katakana_short() -> None:
    """`is_convertible_to_katakana`は2文字以下の英単語を変換可能ではないと判定する"""
    is_convertible = is_convertible_to_katakana(
        pos="フィラー",
        chain_rule="*",
        string="Ｖｏ",
    )

    assert not is_convertible


def test_convert_english_to_katakana() -> None:
    """`convert_english_to_katakana`は英単語をアルファベットそのままで読まない"""
    pron = convert_english_to_katakana("Ｖｏｉｖｏ")

    expected_pron = "ボイボ"

    assert expected_pron == pron
