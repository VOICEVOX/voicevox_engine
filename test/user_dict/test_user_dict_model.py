from typing import TypedDict
from unittest import TestCase

from pydantic import ValidationError

from voicevox_engine.model import UserDictWord
from voicevox_engine.tts_pipeline.kana_converter import parse_kana


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


class TestUserDictWords(TestCase):
    def setUp(self) -> None:
        pass

    def test_valid_word(self) -> None:
        test_value = generate_model()
        try:
            UserDictWord(**test_value)
        except ValidationError as e:
            self.fail(f"Unexpected Validation Error\n{str(e)}")

    def test_convert_to_zenkaku(self) -> None:
        test_value = generate_model()
        test_value["surface"] = "test"
        self.assertEqual(UserDictWord(**test_value).surface, "ｔｅｓｔ")

    def test_count_mora(self) -> None:
        test_value = generate_model()
        self.assertEqual(UserDictWord(**test_value).mora_count, 3)

    def test_count_mora_x(self) -> None:
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
                with self.subTest(s=s, x=x):
                    self.assertEqual(
                        UserDictWord(**test_value).mora_count,
                        expected_count,
                    )

    def test_count_mora_xwa(self) -> None:
        test_value = generate_model()
        test_value["pronunciation"] = "クヮンセイ"
        expected_count = 0
        for accent_phrase in parse_kana(
            test_value["pronunciation"] + "'",
        ):
            expected_count += len(accent_phrase.moras)
        self.assertEqual(
            UserDictWord(**test_value).mora_count,
            expected_count,
        )

    def test_invalid_pronunciation_not_katakana(self) -> None:
        test_value = generate_model()
        test_value["pronunciation"] = "ぼいぼ"
        with self.assertRaises(ValidationError):
            UserDictWord(**test_value)

    def test_invalid_pronunciation_invalid_sutegana(self) -> None:
        test_value = generate_model()
        test_value["pronunciation"] = "アィウェォ"
        with self.assertRaises(ValidationError):
            UserDictWord(**test_value)

    def test_invalid_pronunciation_invalid_xwa(self) -> None:
        test_value = generate_model()
        test_value["pronunciation"] = "アヮ"
        with self.assertRaises(ValidationError):
            UserDictWord(**test_value)

    def test_count_mora_voiced_sound(self) -> None:
        test_value = generate_model()
        test_value["pronunciation"] = "ボイボ"
        self.assertEqual(UserDictWord(**test_value).mora_count, 3)

    def test_invalid_accent_type(self) -> None:
        test_value = generate_model()
        test_value["accent_type"] = 4
        with self.assertRaises(ValidationError):
            UserDictWord(**test_value)

    def test_invalid_accent_type_2(self) -> None:
        test_value = generate_model()
        test_value["accent_type"] = -1
        with self.assertRaises(ValidationError):
            UserDictWord(**test_value)
