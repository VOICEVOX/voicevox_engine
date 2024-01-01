from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from run import generate_app

from voicevox_engine.core_initializer import initialize_cores
from voicevox_engine.preset import PresetManager
from voicevox_engine.setting import CorsPolicyMode, Setting, SettingLoader
from voicevox_engine.tts_pipeline import make_tts_engines_from_cores
from voicevox_engine.utility import engine_root, get_latest_core_version, get_save_dir


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

    def test_dump_from_argument(self):
        """cors policyを指定してgenerate_appを実行したとき、設定ファイルに書き込まれることを確認する"""
        cores = initialize_cores(False)
        tts_engines = make_tts_engines_from_cores(cores)
        latest_core_version = get_latest_core_version(versions=list(tts_engines.keys()))
        setting_loader = SettingLoader(get_save_dir() / "setting.yml")

        preset_manager = PresetManager(
            preset_path=engine_root() / "presets.yaml",
        )

        generate_app(
            tts_engines,
            cores,
            latest_core_version,
            setting_loader,
            preset_manager=preset_manager,
            cors_policy_mode=CorsPolicyMode.all,
        )

        self.assertTrue(setting_loader.setting_file_path.is_file())
        self.assertEqual(
            setting_loader.load_setting_file().dict(),
            {"allow_origin": "*", "cors_policy_mode": CorsPolicyMode.all},
        )

    def tearDown(self):
        self.tmp_dir.cleanup()
