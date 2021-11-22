from unittest import TestCase

from pathlib import Path
from voicevox_engine.preset import PresetLoader


class TestPresetLoader(TestCase):
    def test_validation(self):
        preset_loader = PresetLoader(preset_path=Path("test/presets-test-1.yaml"))
        preset_loader.PRESET_FILE_NAME = "test/presets-test-1.yaml"
        presets, err_detail = preset_loader.load_presets()
        self.assertFalse(presets is None)
        self.assertEqual(err_detail, "")

    def test_validation_2(self):
        preset_loader = PresetLoader(preset_path=Path("test/presets-test-2.yaml"))
        presets, err_detail = preset_loader.load_presets()
        self.assertTrue(presets is None)
        self.assertEqual(err_detail, "プリセットの設定ファイルにミスがあります")

    def test_preset_id(self):
        preset_loader = PresetLoader(preset_path=Path("test/presets-test-3.yaml"))
        presets, err_detail = preset_loader.load_presets()
        self.assertTrue(presets is None)
        self.assertEqual(err_detail, "プリセットのidに重複があります")

    def test_empty_file(self):
        preset_loader = PresetLoader(preset_path=Path("test/presets-test-4.yaml"))
        presets, err_detail = preset_loader.load_presets()
        self.assertTrue(presets is None)
        self.assertEqual(err_detail, "プリセットの設定ファイルが空の内容です")

    def test_not_exist_file(self):
        preset_loader = PresetLoader(preset_path=Path("test/presets-dummy.yaml"))
        presets, err_detail = preset_loader.load_presets()
        self.assertTrue(presets is None)
        self.assertEqual(err_detail, "プリセットの設定ファイルが見つかりません")
