from os import remove
from pathlib import Path
from shutil import copyfile
from tempfile import TemporaryDirectory
from unittest import TestCase

from voicevox_engine.preset import Preset, PresetError, PresetManager


class TestPresetManager(TestCase):
    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.tmp_dir_path = Path(self.tmp_dir.name)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_validation(self):
        preset_manager = PresetManager(preset_path=Path("test/presets-test-1.yaml"))
        presets = preset_manager.load_presets()
        self.assertFalse(presets is None)

    def test_validation_same(self):
        preset_manager = PresetManager(preset_path=Path("test/presets-test-1.yaml"))
        presets = preset_manager.load_presets()
        presets2 = preset_manager.load_presets()
        self.assertFalse(presets is None)
        self.assertEqual(presets, presets2)

    def test_validation_2(self):
        preset_manager = PresetManager(preset_path=Path("test/presets-test-2.yaml"))
        with self.assertRaises(PresetError, msg="プリセットの設定ファイルにミスがあります"):
            preset_manager.load_presets()

    def test_preset_id(self):
        preset_manager = PresetManager(preset_path=Path("test/presets-test-3.yaml"))
        with self.assertRaises(PresetError, msg="プリセットのidに重複があります"):
            preset_manager.load_presets()

    def test_empty_file(self):
        preset_manager = PresetManager(preset_path=Path("test/presets-test-4.yaml"))
        with self.assertRaises(PresetError, msg="プリセットの設定ファイルが空の内容です"):
            preset_manager.load_presets()

    def test_not_exist_file(self):
        preset_manager = PresetManager(preset_path=Path("test/presets-dummy.yaml"))
        with self.assertRaises(PresetError, msg="プリセットの設定ファイルが見つかりません"):
            preset_manager.load_presets()

    def test_add_preset(self):
        temp_path = self.tmp_dir_path / "presets-test-temp.yaml"
        copyfile(Path("test/presets-test-1.yaml"), temp_path)
        preset_manager = PresetManager(preset_path=temp_path)
        preset = Preset(
            **{
                "id": 10,
                "name": "test10",
                "speaker_uuid": "7ffcb7ce-00ec-4bdc-82cd-45a8889e43ff",
                "style_id": 2,
                "speedScale": 1,
                "pitchScale": 1,
                "intonationScale": 0.5,
                "volumeScale": 1,
                "prePhonemeLength": 0.1,
                "postPhonemeLength": 0.1,
            }
        )
        id = preset_manager.add_preset(preset)
        self.assertEqual(id, 10)
        self.assertEqual(len(preset_manager.presets), 3)
        for _preset in preset_manager.presets:
            if _preset.id == id:
                self.assertEqual(_preset, preset)
        remove(temp_path)

    def test_add_preset_load_failure(self):
        preset_manager = PresetManager(preset_path=Path("test/presets-test-2.yaml"))
        with self.assertRaises(PresetError, msg="プリセットの設定ファイルにミスがあります"):
            preset_manager.add_preset(
                Preset(
                    **{
                        "id": 1,
                        "name": "",
                        "speaker_uuid": "",
                        "style_id": 0,
                        "speedScale": 0,
                        "pitchScale": 0,
                        "intonationScale": 0,
                        "volumeScale": 0,
                        "prePhonemeLength": 0,
                        "postPhonemeLength": 0,
                    }
                )
            )

    def test_add_preset_conflict_id(self):
        temp_path = self.tmp_dir_path / "presets-test-temp.yaml"
        copyfile(Path("test/presets-test-1.yaml"), temp_path)
        preset_manager = PresetManager(preset_path=temp_path)
        preset = Preset(
            **{
                "id": 2,
                "name": "test3",
                "speaker_uuid": "7ffcb7ce-00ec-4bdc-82cd-45a8889e43ff",
                "style_id": 2,
                "speedScale": 1,
                "pitchScale": 1,
                "intonationScale": 0.5,
                "volumeScale": 1,
                "prePhonemeLength": 0.1,
                "postPhonemeLength": 0.1,
            }
        )
        id = preset_manager.add_preset(preset)
        self.assertEqual(id, 3)
        self.assertEqual(len(preset_manager.presets), 3)
        for _preset in preset_manager.presets:
            if _preset.id == id:
                self.assertEqual(_preset, preset)
        remove(temp_path)

    def test_add_preset_conflict_id2(self):
        temp_path = self.tmp_dir_path / "presets-test-temp.yaml"
        copyfile(Path("test/presets-test-1.yaml"), temp_path)
        preset_manager = PresetManager(preset_path=temp_path)
        preset = Preset(
            **{
                "id": -1,
                "name": "test3",
                "speaker_uuid": "7ffcb7ce-00ec-4bdc-82cd-45a8889e43ff",
                "style_id": 2,
                "speedScale": 1,
                "pitchScale": 1,
                "intonationScale": 0.5,
                "volumeScale": 1,
                "prePhonemeLength": 0.1,
                "postPhonemeLength": 0.1,
            }
        )
        id = preset_manager.add_preset(preset)
        self.assertEqual(id, 3)
        self.assertEqual(len(preset_manager.presets), 3)
        for _preset in preset_manager.presets:
            if _preset.id == id:
                self.assertEqual(_preset, preset)
        remove(temp_path)

    def test_add_preset_write_failure(self):
        temp_path = self.tmp_dir_path / "presets-test-temp.yaml"
        copyfile(Path("test/presets-test-1.yaml"), temp_path)
        preset_manager = PresetManager(preset_path=temp_path)
        preset = Preset(
            **{
                "id": 10,
                "name": "test10",
                "speaker_uuid": "7ffcb7ce-00ec-4bdc-82cd-45a8889e43ff",
                "style_id": 2,
                "speedScale": 1,
                "pitchScale": 1,
                "intonationScale": 0.5,
                "volumeScale": 1,
                "prePhonemeLength": 0.1,
                "postPhonemeLength": 0.1,
            }
        )
        preset_manager.load_presets()
        preset_manager.load_presets = lambda: []
        preset_manager.preset_path = ""
        with self.assertRaises(PresetError, msg="プリセットの設定ファイルに書き込み失敗しました"):
            preset_manager.add_preset(preset)
        self.assertEqual(len(preset_manager.presets), 2)
        remove(temp_path)

    def test_update_preset(self):
        temp_path = self.tmp_dir_path / "presets-test-temp.yaml"
        copyfile(Path("test/presets-test-1.yaml"), temp_path)
        preset_manager = PresetManager(preset_path=temp_path)
        preset = Preset(
            **{
                "id": 1,
                "name": "test1 new",
                "speaker_uuid": "7ffcb7ce-00ec-4bdc-82cd-45a8889e43ff",
                "style_id": 2,
                "speedScale": 1,
                "pitchScale": 1,
                "intonationScale": 0.5,
                "volumeScale": 1,
                "prePhonemeLength": 0.1,
                "postPhonemeLength": 0.1,
            }
        )
        id = preset_manager.update_preset(preset)
        self.assertEqual(id, 1)
        self.assertEqual(len(preset_manager.presets), 2)
        for _preset in preset_manager.presets:
            if _preset.id == id:
                self.assertEqual(_preset, preset)
        remove(temp_path)

    def test_update_preset_load_failure(self):
        preset_manager = PresetManager(preset_path=Path("test/presets-test-2.yaml"))
        with self.assertRaises(PresetError, msg="プリセットの設定ファイルにミスがあります"):
            preset_manager.update_preset(
                Preset(
                    **{
                        "id": 1,
                        "name": "",
                        "speaker_uuid": "",
                        "style_id": 0,
                        "speedScale": 0,
                        "pitchScale": 0,
                        "intonationScale": 0,
                        "volumeScale": 0,
                        "prePhonemeLength": 0,
                        "postPhonemeLength": 0,
                    }
                )
            )

    def test_update_preset_not_found(self):
        temp_path = self.tmp_dir_path / "presets-test-temp.yaml"
        copyfile(Path("test/presets-test-1.yaml"), temp_path)
        preset_manager = PresetManager(preset_path=temp_path)
        preset = Preset(
            **{
                "id": 10,
                "name": "test1 new",
                "speaker_uuid": "7ffcb7ce-00ec-4bdc-82cd-45a8889e43ff",
                "style_id": 2,
                "speedScale": 1,
                "pitchScale": 1,
                "intonationScale": 0.5,
                "volumeScale": 1,
                "prePhonemeLength": 0.1,
                "postPhonemeLength": 0.1,
            }
        )
        with self.assertRaises(PresetError, msg="更新先のプリセットが存在しません"):
            preset_manager.update_preset(preset)
        self.assertEqual(len(preset_manager.presets), 2)
        remove(temp_path)

    def test_update_preset_write_failure(self):
        temp_path = self.tmp_dir_path / "presets-test-temp.yaml"
        copyfile(Path("test/presets-test-1.yaml"), temp_path)
        preset_manager = PresetManager(preset_path=temp_path)
        preset = Preset(
            **{
                "id": 1,
                "name": "test1 new",
                "speaker_uuid": "7ffcb7ce-00ec-4bdc-82cd-45a8889e43ff",
                "style_id": 2,
                "speedScale": 1,
                "pitchScale": 1,
                "intonationScale": 0.5,
                "volumeScale": 1,
                "prePhonemeLength": 0.1,
                "postPhonemeLength": 0.1,
            }
        )
        preset_manager.load_presets()
        preset_manager.load_presets = lambda: []
        preset_manager.preset_path = ""
        with self.assertRaises(PresetError, msg="プリセットの設定ファイルに書き込み失敗しました"):
            preset_manager.update_preset(preset)
        self.assertEqual(len(preset_manager.presets), 2)
        self.assertEqual(preset_manager.presets[0].name, "test")
        remove(temp_path)

    def test_delete_preset(self):
        temp_path = self.tmp_dir_path / "presets-test-temp.yaml"
        copyfile(Path("test/presets-test-1.yaml"), temp_path)
        preset_manager = PresetManager(preset_path=temp_path)
        id = preset_manager.delete_preset(1)
        self.assertEqual(id, 1)
        self.assertEqual(len(preset_manager.presets), 1)
        remove(temp_path)

    def test_delete_preset_load_failure(self):
        preset_manager = PresetManager(preset_path=Path("test/presets-test-2.yaml"))
        with self.assertRaises(PresetError, msg="プリセットの設定ファイルにミスがあります"):
            preset_manager.delete_preset(10)

    def test_delete_preset_not_found(self):
        temp_path = self.tmp_dir_path / "presets-test-temp.yaml"
        copyfile(Path("test/presets-test-1.yaml"), temp_path)
        preset_manager = PresetManager(preset_path=temp_path)
        with self.assertRaises(PresetError, msg="削除対象のプリセットが存在しません"):
            preset_manager.delete_preset(10)
        self.assertEqual(len(preset_manager.presets), 2)
        remove(temp_path)

    def test_delete_preset_write_failure(self):
        temp_path = self.tmp_dir_path / "presets-test-temp.yaml"
        copyfile(Path("test/presets-test-1.yaml"), temp_path)
        preset_manager = PresetManager(preset_path=temp_path)
        preset_manager.load_presets()
        preset_manager.load_presets = lambda: []
        preset_manager.preset_path = ""
        with self.assertRaises(PresetError, msg="プリセットの設定ファイルに書き込み失敗しました"):
            preset_manager.delete_preset(1)
        self.assertEqual(len(preset_manager.presets), 2)
        remove(temp_path)
