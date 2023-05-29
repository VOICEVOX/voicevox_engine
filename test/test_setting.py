from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from voicevox_engine.setting import CorsPolicyMode, Setting, SettingLoader


class TestSettingLoader(TestCase):
    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.tmp_dir_path = Path(self.tmp_dir.name)

    def test_loading_1(self):
        setting_loader = SettingLoader(Path("not_exist.yaml"))
        settings = setting_loader.load_setting_file()

        self.assertEqual(
            settings.dict(),
            {"allow_origin": None, "cors_policy_mode": CorsPolicyMode.localapps},
        )

    def test_loading_2(self):
        setting_loader = SettingLoader(
            setting_file_path=Path("test/setting-test-load-1.yaml")
        )
        settings = setting_loader.load_setting_file()

        self.assertEqual(
            settings.dict(),
            {"allow_origin": None, "cors_policy_mode": CorsPolicyMode.localapps},
        )

    def test_loading_3(self):
        setting_loader = SettingLoader(
            setting_file_path=Path("test/setting-test-load-2.yaml")
        )
        settings = setting_loader.load_setting_file()

        self.assertEqual(
            settings.dict(),
            {"allow_origin": None, "cors_policy_mode": "all"},
        )

    def test_loading_4(self):
        setting_loader = SettingLoader(
            setting_file_path=Path("test/setting-test-load-3.yaml")
        )
        settings = setting_loader.load_setting_file()

        self.assertEqual(
            settings.dict(),
            {
                "allow_origin": "192.168.254.255 192.168.255.255",
                "cors_policy_mode": CorsPolicyMode.localapps,
            },
        )

    def test_dump(self):
        setting_loader = SettingLoader(
            setting_file_path=Path(self.tmp_dir_path / "setting-test-dump.yaml")
        )
        settings = Setting(cors_policy_mode=CorsPolicyMode.localapps)
        setting_loader.dump_setting_file(settings)

        self.assertTrue(setting_loader.setting_file_path.is_file())
        self.assertEqual(
            setting_loader.load_setting_file().dict(),
            {"allow_origin": None, "cors_policy_mode": CorsPolicyMode.localapps},
        )

    def tearDown(self):
        self.tmp_dir.cleanup()
