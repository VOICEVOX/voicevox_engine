from unittest import TestCase

from run import PresetLoader, mora_to_text


class TestMoraToText(TestCase):
    def test_voice(self):
        self.assertEqual(mora_to_text("a"), "ア")
        self.assertEqual(mora_to_text("i"), "イ")
        self.assertEqual(mora_to_text("ka"), "カ")
        self.assertEqual(mora_to_text("N"), "ン")
        self.assertEqual(mora_to_text("cl"), "ッ")
        self.assertEqual(mora_to_text("gye"), "ギェ")
        self.assertEqual(mora_to_text("ye"), "イェ")
        self.assertEqual(mora_to_text("wo"), "ウォ")

    def test_unvoice(self):
        self.assertEqual(mora_to_text("A"), "ア")
        self.assertEqual(mora_to_text("I"), "イ")
        self.assertEqual(mora_to_text("kA"), "カ")
        self.assertEqual(mora_to_text("gyE"), "ギェ")
        self.assertEqual(mora_to_text("yE"), "イェ")
        self.assertEqual(mora_to_text("wO"), "ウォ")

    def test_invalid_mora(self):
        """変なモーラが来ても例外を投げない"""
        self.assertEqual(mora_to_text("x"), "x")
        self.assertEqual(mora_to_text(""), "")


class TestPresetLoader(TestCase):
    def test_validation(self):
        preset_loader = PresetLoader()
        preset_loader.PRESET_FILE_NAME = "test/presets-test-1.yaml"
        presets, err_detail = preset_loader.load_presets()
        self.assertFalse(presets is None)
        self.assertEqual(err_detail, "")

    def test_validation_2(self):
        preset_loader = PresetLoader()
        preset_loader.PRESET_FILE_NAME = "test/presets-test-2.yaml"
        presets, err_detail = preset_loader.load_presets()
        self.assertTrue(presets is None)
        self.assertEqual(err_detail, "プリセットの設定ファイルにミスがあります")

    def test_preset_id(self):
        preset_loader = PresetLoader()
        preset_loader.PRESET_FILE_NAME = "test/presets-test-3.yaml"
        presets, err_detail = preset_loader.load_presets()
        self.assertTrue(presets is None)
        self.assertEqual(err_detail, "プリセットのidに重複があります")

    def test_empty_file(self):
        preset_loader = PresetLoader()
        preset_loader.PRESET_FILE_NAME = "test/presets-test-4.yaml"
        presets, err_detail = preset_loader.load_presets()
        self.assertTrue(presets is None)
        self.assertEqual(err_detail, "プリセットの設定ファイルが空の内容です")

    def test_not_exist_file(self):
        preset_loader = PresetLoader()
        preset_loader.PRESET_FILE_NAME = "test/presets-dummy.yaml"
        presets, err_detail = preset_loader.load_presets()
        self.assertTrue(presets is None)
        self.assertEqual(err_detail, "プリセットの設定ファイルが見つかりません")
