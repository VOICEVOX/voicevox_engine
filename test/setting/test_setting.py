from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from pydantic import ValidationError

from voicevox_engine.setting import CorsPolicyMode, Setting, SettingHandler


class TestSettingLoader(TestCase):
    def setUp(self) -> None:
        self.tmp_dir = TemporaryDirectory()
        self.tmp_dir_path = Path(self.tmp_dir.name)

    def test_loading_1(self) -> None:
        setting_loader = SettingHandler(Path("not_exist.yaml"))
        settings = setting_loader.load()

        self.assertEqual(
            settings.dict(),
            {"allow_origin": None, "cors_policy_mode": CorsPolicyMode.localapps},
        )

    def test_loading_2(self) -> None:
        setting_loader = SettingHandler(
            setting_file_path=Path("test/setting/setting-test-load-1.yaml")
        )
        settings = setting_loader.load()

        self.assertEqual(
            settings.dict(),
            {"allow_origin": None, "cors_policy_mode": CorsPolicyMode.localapps},
        )

    def test_loading_3(self) -> None:
        setting_loader = SettingHandler(
            setting_file_path=Path("test/setting/setting-test-load-2.yaml")
        )
        settings = setting_loader.load()

        self.assertEqual(
            settings.dict(),
            {"allow_origin": None, "cors_policy_mode": "all"},
        )

    def test_loading_4(self) -> None:
        setting_loader = SettingHandler(
            setting_file_path=Path("test/setting/setting-test-load-3.yaml")
        )
        settings = setting_loader.load()

        self.assertEqual(
            settings.dict(),
            {
                "allow_origin": "192.168.254.255 192.168.255.255",
                "cors_policy_mode": CorsPolicyMode.localapps,
            },
        )

    def test_dump(self) -> None:
        setting_loader = SettingHandler(
            setting_file_path=Path(self.tmp_dir_path / "setting-test-dump.yaml")
        )
        settings = Setting(cors_policy_mode=CorsPolicyMode.localapps)
        setting_loader.save(settings)

        self.assertTrue(setting_loader.setting_file_path.is_file())
        self.assertEqual(
            setting_loader.load().dict(),
            {"allow_origin": None, "cors_policy_mode": CorsPolicyMode.localapps},
        )

    def test_cors_policy_mode_type(self) -> None:
        setting_loader = SettingHandler(
            setting_file_path=Path("test/setting/setting-test-load-1.yaml")
        )
        settings = setting_loader.load()

        self.assertIsInstance(settings.cors_policy_mode, CorsPolicyMode)

    def test_invalid_cors_policy_mode_type(self) -> None:
        with self.assertRaises(ValidationError):
            Setting(cors_policy_mode="invalid_value", allow_origin="*")

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()
