import json
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Dict
from unittest import TestCase

from fastapi import HTTPException
from pyopenjtalk import g2p, unset_user_dict

from voicevox_engine.model import UserDictWord, WordTypes
from voicevox_engine.part_of_speech_data import MAX_PRIORITY, part_of_speech_data
from voicevox_engine.user_dict import (
    apply_word,
    create_word,
    delete_word,
    import_user_dict,
    read_dict,
    rewrite_word,
    update_dict,
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
    accent_associative_rule="*",
)


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
            json.dumps(valid_dict_dict_json, ensure_ascii=False), encoding="utf-8"
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
            json.dumps(valid_dict_dict_json, ensure_ascii=False), encoding="utf-8"
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
            json.dumps(valid_dict_dict_json, ensure_ascii=False), encoding="utf-8"
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
            json.dumps(valid_dict_dict_json, ensure_ascii=False), encoding="utf-8"
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
            json.dumps(valid_dict_dict_json, ensure_ascii=False), encoding="utf-8"
        )
        delete_word(
            word_uuid="aab7dda2-0d97-43c8-8cb7-3f440dab9b4e",
            user_dict_path=user_dict_path,
            compiled_dict_path=(self.tmp_dir_path / "test_delete_word_valid_id.dic"),
        )
        self.assertEqual(len(read_dict(user_dict_path=user_dict_path)), 0)

    def test_priority(self):
        for pos in part_of_speech_data:
            for i in range(MAX_PRIORITY + 1):
                self.assertEqual(
                    create_word(
                        surface="test",
                        pronunciation="テスト",
                        accent_type=1,
                        word_type=pos,
                        priority=i,
                    ).priority,
                    i,
                )

    def test_import_dict(self):
        user_dict_path = self.tmp_dir_path / "test_import_dict.json"
        compiled_dict_path = self.tmp_dir_path / "test_import_dict.dic"
        user_dict_path.write_text(
            json.dumps(valid_dict_dict_json, ensure_ascii=False), encoding="utf-8"
        )
        import_user_dict(
            {"b1affe2a-d5f0-4050-926c-f28e0c1d9a98": import_word},
            override=False,
            user_dict_path=user_dict_path,
            compiled_dict_path=compiled_dict_path,
        )
        self.assertEqual(
            read_dict(user_dict_path)["b1affe2a-d5f0-4050-926c-f28e0c1d9a98"],
            import_word,
        )
        self.assertEqual(
            read_dict(user_dict_path)["aab7dda2-0d97-43c8-8cb7-3f440dab9b4e"],
            UserDictWord(**valid_dict_dict_api["aab7dda2-0d97-43c8-8cb7-3f440dab9b4e"]),
        )

    def test_import_dict_no_override(self):
        user_dict_path = self.tmp_dir_path / "test_import_dict_no_override.json"
        compiled_dict_path = self.tmp_dir_path / "test_import_dict_no_override.dic"
        user_dict_path.write_text(
            json.dumps(valid_dict_dict_json, ensure_ascii=False), encoding="utf-8"
        )
        import_user_dict(
            {"aab7dda2-0d97-43c8-8cb7-3f440dab9b4e": import_word},
            override=False,
            user_dict_path=user_dict_path,
            compiled_dict_path=compiled_dict_path,
        )
        self.assertEqual(
            read_dict(user_dict_path)["aab7dda2-0d97-43c8-8cb7-3f440dab9b4e"],
            UserDictWord(**valid_dict_dict_api["aab7dda2-0d97-43c8-8cb7-3f440dab9b4e"]),
        )

    def test_import_dict_override(self):
        user_dict_path = self.tmp_dir_path / "test_import_dict_override.json"
        compiled_dict_path = self.tmp_dir_path / "test_import_dict_override.dic"
        user_dict_path.write_text(
            json.dumps(valid_dict_dict_json, ensure_ascii=False), encoding="utf-8"
        )
        import_user_dict(
            {"aab7dda2-0d97-43c8-8cb7-3f440dab9b4e": import_word},
            override=True,
            user_dict_path=user_dict_path,
            compiled_dict_path=compiled_dict_path,
        )
        self.assertEqual(
            read_dict(user_dict_path)["aab7dda2-0d97-43c8-8cb7-3f440dab9b4e"],
            import_word,
        )

    def test_import_invalid_word(self):
        user_dict_path = self.tmp_dir_path / "test_import_invalid_dict.json"
        compiled_dict_path = self.tmp_dir_path / "test_import_invalid_dict.dic"
        invalid_accent_associative_rule_word = deepcopy(import_word)
        invalid_accent_associative_rule_word.accent_associative_rule = "invalid"
        user_dict_path.write_text(
            json.dumps(valid_dict_dict_json, ensure_ascii=False), encoding="utf-8"
        )
        self.assertRaises(
            AssertionError,
            import_user_dict,
            {
                "aab7dda2-0d97-43c8-8cb7-3f440dab9b4e": invalid_accent_associative_rule_word
            },
            override=True,
            user_dict_path=user_dict_path,
            compiled_dict_path=compiled_dict_path,
        )
        invalid_pos_word = deepcopy(import_word)
        invalid_pos_word.context_id = 2
        invalid_pos_word.part_of_speech = "フィラー"
        invalid_pos_word.part_of_speech_detail_1 = "*"
        invalid_pos_word.part_of_speech_detail_2 = "*"
        invalid_pos_word.part_of_speech_detail_3 = "*"
        self.assertRaises(
            ValueError,
            import_user_dict,
            {"aab7dda2-0d97-43c8-8cb7-3f440dab9b4e": invalid_pos_word},
            override=True,
            user_dict_path=user_dict_path,
            compiled_dict_path=compiled_dict_path,
        )

    def test_update_dict(self):
        user_dict_path = self.tmp_dir_path / "test_update_dict.json"
        compiled_dict_path = self.tmp_dir_path / "test_update_dict.dic"
        update_dict(
            user_dict_path=user_dict_path, compiled_dict_path=compiled_dict_path
        )
        test_text = "テスト用の文字列"
        success_pronunciation = "デフォルトノジショデハゼッタイニセイセイサレナイヨミ"

        # 既に辞書に登録されていないか確認する
        self.assertNotEqual(g2p(text=test_text, kana=True), success_pronunciation)

        apply_word(
            surface=test_text,
            pronunciation=success_pronunciation,
            accent_type=1,
            priority=10,
            user_dict_path=user_dict_path,
            compiled_dict_path=compiled_dict_path,
        )
        self.assertEqual(g2p(text=test_text, kana=True), success_pronunciation)

        # 疑似的にエンジンを再起動する
        unset_user_dict()
        update_dict(
            user_dict_path=user_dict_path, compiled_dict_path=compiled_dict_path
        )

        self.assertEqual(g2p(text=test_text, kana=True), success_pronunciation)
