import json
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from pyopenjtalk import g2p, unset_user_dict

from voicevox_engine.model import UserDictWord, WordTypes
from voicevox_engine.user_dict.part_of_speech_data import (
    MAX_PRIORITY,
    part_of_speech_data,
)
from voicevox_engine.user_dict.user_dict import (
    UserDictInputError,
    UserDictionary,
    _create_word,
)

# jsonとして保存される正しい形式の辞書データ
valid_dict_dict_json = {
    "aab7dda2-0d97-43c8-8cb7-3f440dab9b4e": {
        "surface": "ｔｅｓｔ",
        "cost": part_of_speech_data[WordTypes.PROPER_NOUN].cost_candidates[5],
        "part_of_speech": "名詞",
        "part_of_speech_detail_1": "固有名詞",
        "part_of_speech_detail_2": "一般",
        "part_of_speech_detail_3": "*",
        "inflectional_type": "*",
        "inflectional_form": "*",
        "stem": "*",
        "yomi": "テスト",
        "pronunciation": "テスト",
        "accent_type": 1,
        "accent_associative_rule": "*",
    },
}

# APIでやり取りされる正しい形式の辞書データ
valid_dict_dict_api = deepcopy(valid_dict_dict_json)
del valid_dict_dict_api["aab7dda2-0d97-43c8-8cb7-3f440dab9b4e"]["cost"]
valid_dict_dict_api["aab7dda2-0d97-43c8-8cb7-3f440dab9b4e"]["priority"] = 5

import_word = UserDictWord(
    surface="ｔｅｓｔ２",
    priority=5,
    part_of_speech="名詞",
    part_of_speech_detail_1="固有名詞",
    part_of_speech_detail_2="一般",
    part_of_speech_detail_3="*",
    inflectional_type="*",
    inflectional_form="*",
    stem="*",
    yomi="テストツー",
    pronunciation="テストツー",
    accent_type=1,
    mora_count=None,
    accent_associative_rule="*",
)


def get_new_word(user_dict: dict[str, UserDictWord]) -> UserDictWord:
    assert len(user_dict) == 2 or (
        len(user_dict) == 1 and "aab7dda2-0d97-43c8-8cb7-3f440dab9b4e" not in user_dict
    )
    for word_uuid in user_dict.keys():
        if word_uuid == "aab7dda2-0d97-43c8-8cb7-3f440dab9b4e":
            continue
        return user_dict[word_uuid]
    raise AssertionError


class TestUserDict(TestCase):
    def setUp(self) -> None:
        self.tmp_dir = TemporaryDirectory()
        self.tmp_dir_path = Path(self.tmp_dir.name)

    def tearDown(self) -> None:
        unset_user_dict()
        self.tmp_dir.cleanup()

    def test_read_not_exist_json(self) -> None:
        user_dict = UserDictionary(user_dict_path=self.tmp_dir_path / "not_exist.json")
        self.assertEqual(
            user_dict.read_dict(),
            {},
        )

    def test_create_word(self) -> None:
        # 将来的に品詞などが追加された時にテストを増やす
        self.assertEqual(
            _create_word(
                surface="test",
                pronunciation="テスト",
                accent_type=1,
                word_type=None,
                priority=None,
            ),
            UserDictWord(
                surface="ｔｅｓｔ",
                priority=5,
                part_of_speech="名詞",
                part_of_speech_detail_1="固有名詞",
                part_of_speech_detail_2="一般",
                part_of_speech_detail_3="*",
                inflectional_type="*",
                inflectional_form="*",
                stem="*",
                yomi="テスト",
                pronunciation="テスト",
                accent_type=1,
                mora_count=None,
                accent_associative_rule="*",
            ),
        )

    def test_apply_word_without_json(self) -> None:

        user_dict = UserDictionary(
            user_dict_path=self.tmp_dir_path / "test_apply_word_without_json.json",
            compiled_dict_path=self.tmp_dir_path / "test_apply_word_without_json.dic",
        )
        user_dict.apply_word(surface="test", pronunciation="テスト", accent_type=1)
        res = user_dict.read_dict()
        self.assertEqual(len(res), 1)
        new_word = get_new_word(res)
        self.assertEqual(
            (
                new_word.surface,
                new_word.pronunciation,
                new_word.accent_type,
            ),
            ("ｔｅｓｔ", "テスト", 1),
        )

    def test_apply_word_with_json(self) -> None:
        user_dict_path = self.tmp_dir_path / "test_apply_word_with_json.json"
        user_dict_path.write_text(
            json.dumps(valid_dict_dict_json, ensure_ascii=False), encoding="utf-8"
        )
        user_dict = UserDictionary(
            user_dict_path=user_dict_path,
            compiled_dict_path=self.tmp_dir_path / "test_apply_word_with_json.dic",
        )
        user_dict.apply_word(
            surface="test2",
            pronunciation="テストツー",
            accent_type=3,
        )
        res = user_dict.read_dict()
        self.assertEqual(len(res), 2)
        new_word = get_new_word(res)
        self.assertEqual(
            (
                new_word.surface,
                new_word.pronunciation,
                new_word.accent_type,
            ),
            ("ｔｅｓｔ２", "テストツー", 3),
        )

    def test_rewrite_word_invalid_id(self) -> None:
        user_dict_path = self.tmp_dir_path / "test_rewrite_word_invalid_id.json"
        user_dict_path.write_text(
            json.dumps(valid_dict_dict_json, ensure_ascii=False), encoding="utf-8"
        )
        user_dict = UserDictionary(
            user_dict_path=user_dict_path,
            compiled_dict_path=(self.tmp_dir_path / "test_rewrite_word_invalid_id.dic"),
        )
        self.assertRaises(
            UserDictInputError,
            user_dict.rewrite_word,
            word_uuid="c2be4dc5-d07d-4767-8be1-04a1bb3f05a9",
            surface="test2",
            pronunciation="テストツー",
            accent_type=2,
        )

    def test_rewrite_word_valid_id(self) -> None:
        user_dict_path = self.tmp_dir_path / "test_rewrite_word_valid_id.json"
        user_dict_path.write_text(
            json.dumps(valid_dict_dict_json, ensure_ascii=False), encoding="utf-8"
        )
        user_dict = UserDictionary(
            user_dict_path=user_dict_path,
            compiled_dict_path=self.tmp_dir_path / "test_rewrite_word_valid_id.dic",
        )
        user_dict.rewrite_word(
            word_uuid="aab7dda2-0d97-43c8-8cb7-3f440dab9b4e",
            surface="test2",
            pronunciation="テストツー",
            accent_type=2,
        )
        new_word = user_dict.read_dict()["aab7dda2-0d97-43c8-8cb7-3f440dab9b4e"]
        self.assertEqual(
            (new_word.surface, new_word.pronunciation, new_word.accent_type),
            ("ｔｅｓｔ２", "テストツー", 2),
        )

    def test_delete_word_invalid_id(self) -> None:
        user_dict_path = self.tmp_dir_path / "test_delete_word_invalid_id.json"
        user_dict_path.write_text(
            json.dumps(valid_dict_dict_json, ensure_ascii=False), encoding="utf-8"
        )
        user_dict = UserDictionary(
            user_dict_path=user_dict_path,
            compiled_dict_path=self.tmp_dir_path / "test_delete_word_invalid_id.dic",
        )
        self.assertRaises(
            UserDictInputError,
            user_dict.delete_word,
            word_uuid="c2be4dc5-d07d-4767-8be1-04a1bb3f05a9",
        )

    def test_delete_word_valid_id(self) -> None:
        user_dict_path = self.tmp_dir_path / "test_delete_word_valid_id.json"
        user_dict_path.write_text(
            json.dumps(valid_dict_dict_json, ensure_ascii=False), encoding="utf-8"
        )
        user_dict = UserDictionary(
            user_dict_path=user_dict_path,
            compiled_dict_path=self.tmp_dir_path / "test_delete_word_valid_id.dic",
        )
        user_dict.delete_word(word_uuid="aab7dda2-0d97-43c8-8cb7-3f440dab9b4e")
        self.assertEqual(len(user_dict.read_dict()), 0)

    def test_priority(self) -> None:
        for pos in part_of_speech_data:
            for i in range(MAX_PRIORITY + 1):
                self.assertEqual(
                    _create_word(
                        surface="test",
                        pronunciation="テスト",
                        accent_type=1,
                        word_type=pos,
                        priority=i,
                    ).priority,
                    i,
                )

    def test_import_dict(self) -> None:
        user_dict_path = self.tmp_dir_path / "test_import_dict.json"
        compiled_dict_path = self.tmp_dir_path / "test_import_dict.dic"
        user_dict_path.write_text(
            json.dumps(valid_dict_dict_json, ensure_ascii=False), encoding="utf-8"
        )
        user_dict = UserDictionary(
            user_dict_path=user_dict_path, compiled_dict_path=compiled_dict_path
        )
        user_dict.import_user_dict(
            {"b1affe2a-d5f0-4050-926c-f28e0c1d9a98": import_word}, override=False
        )
        self.assertEqual(
            user_dict.read_dict()["b1affe2a-d5f0-4050-926c-f28e0c1d9a98"],
            import_word,
        )
        self.assertEqual(
            user_dict.read_dict()["aab7dda2-0d97-43c8-8cb7-3f440dab9b4e"],
            UserDictWord(**valid_dict_dict_api["aab7dda2-0d97-43c8-8cb7-3f440dab9b4e"]),
        )

    def test_import_dict_no_override(self) -> None:
        user_dict_path = self.tmp_dir_path / "test_import_dict_no_override.json"
        compiled_dict_path = self.tmp_dir_path / "test_import_dict_no_override.dic"
        user_dict_path.write_text(
            json.dumps(valid_dict_dict_json, ensure_ascii=False), encoding="utf-8"
        )
        user_dict = UserDictionary(
            user_dict_path=user_dict_path, compiled_dict_path=compiled_dict_path
        )
        user_dict.import_user_dict(
            {"aab7dda2-0d97-43c8-8cb7-3f440dab9b4e": import_word}, override=False
        )
        self.assertEqual(
            user_dict.read_dict()["aab7dda2-0d97-43c8-8cb7-3f440dab9b4e"],
            UserDictWord(**valid_dict_dict_api["aab7dda2-0d97-43c8-8cb7-3f440dab9b4e"]),
        )

    def test_import_dict_override(self) -> None:
        user_dict_path = self.tmp_dir_path / "test_import_dict_override.json"
        compiled_dict_path = self.tmp_dir_path / "test_import_dict_override.dic"
        user_dict_path.write_text(
            json.dumps(valid_dict_dict_json, ensure_ascii=False), encoding="utf-8"
        )
        user_dict = UserDictionary(
            user_dict_path=user_dict_path, compiled_dict_path=compiled_dict_path
        )
        user_dict.import_user_dict(
            {"aab7dda2-0d97-43c8-8cb7-3f440dab9b4e": import_word}, override=True
        )
        self.assertEqual(
            user_dict.read_dict()["aab7dda2-0d97-43c8-8cb7-3f440dab9b4e"],
            import_word,
        )

    def test_import_invalid_word(self) -> None:
        user_dict_path = self.tmp_dir_path / "test_import_invalid_dict.json"
        compiled_dict_path = self.tmp_dir_path / "test_import_invalid_dict.dic"
        invalid_accent_associative_rule_word = deepcopy(import_word)
        invalid_accent_associative_rule_word.accent_associative_rule = "invalid"
        user_dict_path.write_text(
            json.dumps(valid_dict_dict_json, ensure_ascii=False), encoding="utf-8"
        )
        user_dict = UserDictionary(
            user_dict_path=user_dict_path, compiled_dict_path=compiled_dict_path
        )
        self.assertRaises(
            AssertionError,
            user_dict.import_user_dict,
            {
                "aab7dda2-0d97-43c8-8cb7-3f440dab9b4e": invalid_accent_associative_rule_word
            },
            override=True,
        )
        invalid_pos_word = deepcopy(import_word)
        invalid_pos_word.context_id = 2
        invalid_pos_word.part_of_speech = "フィラー"
        invalid_pos_word.part_of_speech_detail_1 = "*"
        invalid_pos_word.part_of_speech_detail_2 = "*"
        invalid_pos_word.part_of_speech_detail_3 = "*"
        self.assertRaises(
            ValueError,
            user_dict.import_user_dict,
            {"aab7dda2-0d97-43c8-8cb7-3f440dab9b4e": invalid_pos_word},
            override=True,
        )

    def test_update_dict(self) -> None:
        user_dict_path = self.tmp_dir_path / "test_update_dict.json"
        compiled_dict_path = self.tmp_dir_path / "test_update_dict.dic"
        user_dict = UserDictionary(
            user_dict_path=user_dict_path, compiled_dict_path=compiled_dict_path
        )
        user_dict.update_dict()
        test_text = "テスト用の文字列"
        success_pronunciation = "デフォルトノジショデハゼッタイニセイセイサレナイヨミ"

        # 既に辞書に登録されていないか確認する
        self.assertNotEqual(g2p(text=test_text, kana=True), success_pronunciation)

        user_dict.apply_word(
            surface=test_text,
            pronunciation=success_pronunciation,
            accent_type=1,
            priority=10,
        )
        self.assertEqual(g2p(text=test_text, kana=True), success_pronunciation)

        # 疑似的にエンジンを再起動する
        unset_user_dict()
        user_dict.update_dict()

        self.assertEqual(g2p(text=test_text, kana=True), success_pronunciation)
