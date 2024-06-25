from pathlib import Path

from voicevox_engine.setting.model import CorsPolicyMode
from voicevox_engine.setting.setting_manager import Setting, SettingHandler


def test_setting_handler_load_not_exist_file() -> None:
    """`SettingHandler` に存在しない設定ファイルのパスを渡すとデフォルト値になる。"""
    # Inputs
    setting_path = Path("not_exist.yaml")
    setting_loader = SettingHandler(setting_path)
    # Expects
    true_setting = Setting(cors_policy_mode=CorsPolicyMode.localapps, allow_origin=None)
    # Outputs
    setting = setting_loader.load()
    # Test
    assert true_setting == setting


def test_setting_handler_load_exist_file_1() -> None:
    """`SettingHandler` に設定ファイルのパスを渡すとその値を読み込む。"""
    # Inputs
    setting_path = Path("test/unit/setting/setting-test-load-1.yaml")
    setting_loader = SettingHandler(setting_path)
    # Expects
    true_setting = Setting(cors_policy_mode=CorsPolicyMode.localapps, allow_origin=None)
    # Outputs
    setting = setting_loader.load()
    # Test
    assert true_setting == setting


def test_setting_handler_load_exist_file_2() -> None:
    """`SettingHandler` に設定ファイルのパスを渡すとその値を読み込む。"""
    # Inputs
    setting_path = Path("test/unit/setting/setting-test-load-2.yaml")
    setting_loader = SettingHandler(setting_path)
    # Expects
    true_setting = Setting(cors_policy_mode=CorsPolicyMode.all, allow_origin=None)
    # Outputs
    setting = setting_loader.load()
    # Test
    assert true_setting == setting


def test_setting_handler_load_exist_file_3() -> None:
    """`SettingHandler` に設定ファイルのパスを渡すとその値を読み込む。"""
    # Inputs
    setting_path = Path("test/unit/setting/setting-test-load-3.yaml")
    setting_loader = SettingHandler(setting_path)
    # Expects
    true_policy = CorsPolicyMode.localapps
    true_origin = "192.168.254.255 192.168.255.255"
    true_setting = Setting(cors_policy_mode=true_policy, allow_origin=true_origin)
    # Outputs
    setting = setting_loader.load()
    # Test
    assert true_setting == setting


def test_setting_handler_save(tmp_path: Path) -> None:
    """`SettingHandler.save()` で設定値を保存できる。"""
    # Inputs
    setting_path = tmp_path / "setting-test-dump.yaml"
    setting_loader = SettingHandler(setting_path)
    new_setting = Setting(cors_policy_mode=CorsPolicyMode.localapps)
    # Expects
    true_setting = Setting(cors_policy_mode=CorsPolicyMode.localapps, allow_origin=None)
    # Outputs
    setting_loader.save(new_setting)
    setting = setting_loader.load()  # NOTE: `.load()` の正常動作を前提とする
    # Test
    assert true_setting == setting
