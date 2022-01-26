from copy import deepcopy
from unittest import TestCase

from pydantic import ValidationError

from voicevox_engine.model import UserDictWord


class TestUserDictWords(TestCase):
    def setUp(self):
        self.test_model = {
            "surface": "テスト",
            "cost": 0,
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
            "accent_associative_rule": "*",
        }

    def test_convert_to_zenkaku(self):
        test_value = deepcopy(self.test_model)
        test_value["surface"] = "test"
        self.assertEqual(UserDictWord(**test_value).surface, "ｔｅｓｔ")

    def test_count_mora(self):
        test_value = deepcopy(self.test_model)
        self.assertEqual(UserDictWord(**test_value).mora_count, 3)

    def test_invalid_accent_type(self):
        test_value = deepcopy(self.test_model)
        test_value["accent_type"] = 4
        with self.assertRaises(ValidationError):
            UserDictWord(**test_value)
