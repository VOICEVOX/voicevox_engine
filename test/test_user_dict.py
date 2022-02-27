import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Dict
from unittest import TestCase

from fastapi import HTTPException
from pyopenjtalk import unset_user_dict

from voicevox_engine.model import UserDictWord
from voicevox_engine.user_dict import (
    apply_word,
    create_word,
    delete_word,
    read_dict,
    rewrite_word,
)

valid_dict_dict = {
    "aab7dda2-0d97-43c8-8cb7-3f440dab9b4e": {
        "surface": "ｔｅｓｔ",
        "cost": 8600,
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


def get_new_word(user_dict: Dict[str, UserDictWord]):
    assert len(user_dict) == 2 or (
        len(user_dict) == 1 and "aab7dda2-0d97-43c8-8cb7-3f440dab9b4e" not in user_dict
    )
    for word_uuid in user_dict.keys():
        if word_uuid == "aab7dda2-0d97-43c8-8cb7-3f440dab9b4e":
            continue
        return user_dict[word_uuid]
    raise AssertionError


class TestUserDict(TestCase):
    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.tmp_dir_path = Path(self.tmp_dir.name)

    def tearDown(self):
        unset_user_dict()
        self.tmp_dir.cleanup()

    def test_read_not_exist_json(self):
        self.assertEqual(
            read_dict(user_dict_path=(self.tmp_dir_path / "not_exist.json")),
            {},
        )

    def test_create_word(self):
        # 将来的に品詞などが追加された時にテストを増やす
        self.assertEqual(
            create_word(surface="test", pronunciation="テスト", accent_type=1),
            UserDictWord(
                surface="ｔｅｓｔ",
                cost=8600,
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
                accent_associative_rule="*",
            ),
        )

    def test_apply_word_without_json(self):
        user_dict_path = self.tmp_dir_path / "test_apply_word_without_json.json"
        apply_word(
            surface="test",
            pronunciation="テスト",
            accent_type=1,
            user_dict_path=user_dict_path,
            compiled_dict_path=(self.tmp_dir_path / "test_apply_word_without_json.dic"),
        )
        res = read_dict(user_dict_path=user_dict_path)
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

    def test_apply_word_with_json(self):
        user_dict_path = self.tmp_dir_path / "test_apply_word_with_json.json"
        user_dict_path.write_text(
            json.dumps(valid_dict_dict, ensure_ascii=False), encoding="utf-8"
        )
        apply_word(
            surface="test2",
            pronunciation="テストツー",
            accent_type=3,
            user_dict_path=user_dict_path,
            compiled_dict_path=(self.tmp_dir_path / "test_apply_word_with_json.dic"),
        )
        res = read_dict(user_dict_path=user_dict_path)
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

    def test_rewrite_word_invalid_id(self):
        user_dict_path = self.tmp_dir_path / "test_rewrite_word_invalid_id.json"
        user_dict_path.write_text(
            json.dumps(valid_dict_dict, ensure_ascii=False), encoding="utf-8"
        )
        self.assertRaises(
            HTTPException,
            rewrite_word,
            word_uuid="c2be4dc5-d07d-4767-8be1-04a1bb3f05a9",
            surface="test2",
            pronunciation="テストツー",
            accent_type=2,
            user_dict_path=user_dict_path,
            compiled_dict_path=(self.tmp_dir_path / "test_rewrite_word_invalid_id.dic"),
        )

    def test_rewrite_word_valid_id(self):
        user_dict_path = self.tmp_dir_path / "test_rewrite_word_valid_id.json"
        user_dict_path.write_text(
            json.dumps(valid_dict_dict, ensure_ascii=False), encoding="utf-8"
        )
        rewrite_word(
            word_uuid="aab7dda2-0d97-43c8-8cb7-3f440dab9b4e",
            surface="test2",
            pronunciation="テストツー",
            accent_type=2,
            user_dict_path=user_dict_path,
            compiled_dict_path=(self.tmp_dir_path / "test_rewrite_word_valid_id.dic"),
        )
        new_word = read_dict(user_dict_path=user_dict_path)[
            "aab7dda2-0d97-43c8-8cb7-3f440dab9b4e"
        ]
        self.assertEqual(
            (new_word.surface, new_word.pronunciation, new_word.accent_type),
            ("ｔｅｓｔ２", "テストツー", 2),
        )

    def test_delete_word_invalid_id(self):
        user_dict_path = self.tmp_dir_path / "test_delete_word_invalid_id.json"
        user_dict_path.write_text(
            json.dumps(valid_dict_dict, ensure_ascii=False), encoding="utf-8"
        )
        self.assertRaises(
            HTTPException,
            delete_word,
            word_uuid="c2be4dc5-d07d-4767-8be1-04a1bb3f05a9",
            user_dict_path=user_dict_path,
            compiled_dict_path=(self.tmp_dir_path / "test_delete_word_invalid_id.dic"),
        )

    def test_delete_word_valid_id(self):
        user_dict_path = self.tmp_dir_path / "test_delete_word_valid_id.json"
        user_dict_path.write_text(
            json.dumps(valid_dict_dict, ensure_ascii=False), encoding="utf-8"
        )
        delete_word(
            word_uuid="aab7dda2-0d97-43c8-8cb7-3f440dab9b4e",
            user_dict_path=user_dict_path,
            compiled_dict_path=(self.tmp_dir_path / "test_delete_word_valid_id.dic"),
        )
        self.assertEqual(len(read_dict(user_dict_path=user_dict_path)), 0)
