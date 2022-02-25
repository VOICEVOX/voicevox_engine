import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from fastapi import HTTPException
from pyopenjtalk import unset_user_dict

from voicevox_engine.model import UserDictJson, UserDictWord
from voicevox_engine.user_dict import (
    apply_word,
    create_word,
    delete_word,
    read_dict,
    rewrite_word,
)

valid_dict_dict = {
    "next_id": 1,
    "words": {
        "0": {
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
        }
    },
}


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
            UserDictJson(**{"next_id": 0, "words": {}}),
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
        self.assertEqual(len(res.words), 1)
        self.assertEqual(res.next_id, 1)
        self.assertEqual(
            (
                res.words[0].surface,
                res.words[0].pronunciation,
                res.words[0].accent_type,
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
        self.assertEqual(len(res.words), 2)
        self.assertEqual(res.next_id, 2)
        self.assertEqual(
            (
                res.words[1].surface,
                res.words[1].pronunciation,
                res.words[1].accent_type,
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
            id=1,
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
            id=0,
            surface="test2",
            pronunciation="テストツー",
            accent_type=2,
            user_dict_path=user_dict_path,
            compiled_dict_path=(self.tmp_dir_path / "test_rewrite_word_valid_id.dic"),
        )
        res = read_dict(user_dict_path=user_dict_path).words[0]
        self.assertEqual(
            (res.surface, res.pronunciation, res.accent_type), ("ｔｅｓｔ２", "テストツー", 2)
        )

    def test_delete_word_invalid_id(self):
        user_dict_path = self.tmp_dir_path / "test_delete_word_invalid_id.json"
        user_dict_path.write_text(
            json.dumps(valid_dict_dict, ensure_ascii=False), encoding="utf-8"
        )
        self.assertRaises(
            HTTPException,
            delete_word,
            id=1,
            user_dict_path=user_dict_path,
            compiled_dict_path=(self.tmp_dir_path / "test_delete_word_invalid_id.dic"),
        )

    def test_delete_word_valid_id(self):
        user_dict_path = self.tmp_dir_path / "test_delete_word_valid_id.json"
        user_dict_path.write_text(
            json.dumps(valid_dict_dict, ensure_ascii=False), encoding="utf-8"
        )
        delete_word(
            id=0,
            user_dict_path=user_dict_path,
            compiled_dict_path=(self.tmp_dir_path / "test_delete_word_valid_id.dic"),
        )
        self.assertEqual(len(read_dict(user_dict_path=user_dict_path).words), 0)
