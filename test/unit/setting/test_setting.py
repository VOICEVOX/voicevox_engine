from pathlib import Path

import pytest
from pydantic import ValidationError

from voicevox_engine.setting.model import CorsPolicyMode
from voicevox_engine.setting.setting_manager import Setting, SettingHandler


def test_setting_handler_load_not_exist_file() -> None:
    """`SettingHandler` に存在しない設定ファイルのパスを渡すとデフォルト値になる。"""
    # Inputs
    setting_loader = SettingHandler(Path("not_exist.yaml"))
    # Expects
    true_cors_policy_mode = CorsPolicyMode.localapps
    true_allow_origin = None
    # Outputs
    cors_policy_mode, allow_origin = setting_loader.load()
    # Test
    assert true_cors_policy_mode == cors_policy_mode
    assert true_allow_origin == allow_origin


def test_setting_handler_load_exist_file_1() -> None:
    """`SettingHandler` に設定ファイルのパスを渡すとその値を読み込む。"""
    # Inputs
    setting_path = Path("test/unit/setting/setting-test-load-1.yaml")
    setting_loader = SettingHandler(setting_path)
    # Expects
    true_cors_policy_mode = CorsPolicyMode.localapps
    true_allow_origin = None
    # Outputs
    cors_policy_mode, allow_origin = setting_loader.load()
    # Test
    assert true_cors_policy_mode == cors_policy_mode
    assert true_allow_origin == allow_origin


def test_setting_handler_load_exist_file_2() -> None:
    """`SettingHandler` に設定ファイルのパスを渡すとその値を読み込む。"""
    # Inputs
    setting_path = Path("test/unit/setting/setting-test-load-2.yaml")
    setting_loader = SettingHandler(setting_path)
    cors_policy_mode, allow_origin = setting_loader.load()
    # Expects
    true_cors_policy_mode = CorsPolicyMode.all
    true_allow_origin = None
    # Outputs
    cors_policy_mode, allow_origin = setting_loader.load()
    # Test
    assert true_cors_policy_mode == cors_policy_mode
    assert true_allow_origin == allow_origin


def test_setting_handler_load_exist_file_3() -> None:
    """`SettingHandler` に設定ファイルのパスを渡すとその値を読み込む。"""
    # Inputs
    setting_path = Path("test/unit/setting/setting-test-load-3.yaml")
    setting_loader = SettingHandler(setting_path)
    cors_policy_mode, allow_origin = setting_loader.load()
    # Expects
    true_cors_policy_mode = CorsPolicyMode.localapps
    true_allow_origin = "192.168.254.255 192.168.255.255"
    # Outputs
    cors_policy_mode, allow_origin = setting_loader.load()
    # Test
    assert true_cors_policy_mode == cors_policy_mode
    assert true_allow_origin == allow_origin


def test_setting_handler_save(tmp_path: Path) -> None:
    """`SettingHandler.save()` で設定値を保存できる。"""
    # Inputs
    setting_path = tmp_path / "setting-test-dump.yaml"
    setting_loader = SettingHandler(setting_path)
    new_setting_cors = CorsPolicyMode.localapps
    new_setting_origin = None
    # Expects
    true_cors_policy_mode = CorsPolicyMode.localapps
    true_allow_origin = None
    # Outputs
    setting_loader.save(new_setting_cors, new_setting_origin)
    # NOTE: `.load()` の正常動作を前提とする
    cors_policy_mode, allow_origin = setting_loader.load()
    # Test
    assert true_cors_policy_mode == cors_policy_mode
    assert true_allow_origin == allow_origin


def test_setting_invalid_input() -> None:
    """`Setting` は不正な入力に対してエラーを送出する。"""
    # Test
    with pytest.raises(ValidationError) as _:
        Setting(cors_policy_mode="invalid_value", allow_origin="*")
