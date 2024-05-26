from typing import TypedDict

import pytest
from pydantic import ValidationError

from voicevox_engine.tts_pipeline.kana_converter import parse_kana
from voicevox_engine.user_dict.part_of_speech_data import UserDictWord


class TestModel(TypedDict):
    surface: str
    priority: int
    part_of_speech: str
    part_of_speech_detail_1: str
    part_of_speech_detail_2: str
    part_of_speech_detail_3: str
    inflectional_type: str
    inflectional_form: str
    stem: str
    yomi: str
    pronunciation: str
    accent_type: int
    mora_count: int | None
    accent_associative_rule: str


def generate_model() -> TestModel:
    return {
        "surface": "テスト",
        "priority": 0,
        "part_of_speech": "名詞",
        "part_of_speech_detail_1": "固有名詞",
        "part_of_speech_detail_2": "一般",
        "part_of_speech_detail_3": "*",
        "inflectional_type": "*",
        "inflectional_form": "*",
        "stem": "*",
        "yomi": "テスト",
        "pronunciation": "テスト",
        "accent_type": 0,
        "mora_count": None,
        "accent_associative_rule": "*",
    }


def test_valid_word() -> None:
    test_value = generate_model()
    UserDictWord(**test_value)


def test_convert_to_zenkaku() -> None:
    test_value = generate_model()
    test_value["surface"] = "test"
    assert UserDictWord(**test_value).surface == "ｔｅｓｔ"


def test_count_mora() -> None:
    test_value = generate_model()
    assert UserDictWord(**test_value).mora_count == 3


def test_count_mora_x() -> None:
    test_value = generate_model()
    for s in [chr(i) for i in range(12449, 12533)]:
        if s in ["ァ", "ィ", "ゥ", "ェ", "ォ", "ッ", "ャ", "ュ", "ョ", "ヮ"]:
            continue
        for x in "ァィゥェォャュョ":
            expected_count = 0
            test_value["pronunciation"] = s + x
            for accent_phrase in parse_kana(
                test_value["pronunciation"] + "'",
            ):
                expected_count += len(accent_phrase.moras)
                assert UserDictWord(**test_value).mora_count == expected_count


def test_count_mora_xwa() -> None:
    test_value = generate_model()
    test_value["pronunciation"] = "クヮンセイ"
    expected_count = 0
    for accent_phrase in parse_kana(
        test_value["pronunciation"] + "'",
    ):
        expected_count += len(accent_phrase.moras)
    assert UserDictWord(**test_value).mora_count == expected_count


def test_invalid_pronunciation_not_katakana() -> None:
    test_value = generate_model()
    test_value["pronunciation"] = "ぼいぼ"
    with pytest.raises(ValidationError):
        UserDictWord(**test_value)


def test_invalid_pronunciation_invalid_sutegana() -> None:
    test_value = generate_model()
    test_value["pronunciation"] = "アィウェォ"
    with pytest.raises(ValidationError):
        UserDictWord(**test_value)


def test_invalid_pronunciation_invalid_xwa() -> None:
    test_value = generate_model()
    test_value["pronunciation"] = "アヮ"
    with pytest.raises(ValidationError):
        UserDictWord(**test_value)


def test_count_mora_voiced_sound() -> None:
    test_value = generate_model()
    test_value["pronunciation"] = "ボイボ"
    assert UserDictWord(**test_value).mora_count == 3


def test_invalid_accent_type() -> None:
    test_value = generate_model()
    test_value["accent_type"] = 4
    with pytest.raises(ValidationError):
        UserDictWord(**test_value)


def test_invalid_accent_type_2() -> None:
    test_value = generate_model()
    test_value["accent_type"] = -1
    with pytest.raises(ValidationError):
        UserDictWord(**test_value)
