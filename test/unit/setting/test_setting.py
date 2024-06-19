from pathlib import Path

import pytest
from pydantic import ValidationError

from voicevox_engine.setting.model import CorsPolicyMode
from voicevox_engine.setting.setting_manager import (
    Setting,
    SettingHandler,
    _setting_adapter,
)


def test_setting_handler_load_not_exist_file() -> None:
    """`SettingHandler` に存在しない設定ファイルのパスを渡すとデフォルト値になる。"""
    # Inputs
    setting_loader = SettingHandler(Path("not_exist.yaml"))
    settings = setting_loader.load()
    # Expects
    true_setting = {"allow_origin": None, "cors_policy_mode": CorsPolicyMode.localapps}
    # Outputs
    setting = _setting_adapter.dump_python(settings)
    # Test
    assert true_setting == setting


def test_setting_handler_load_exist_file_1() -> None:
    """`SettingHandler` に設定ファイルのパスを渡すとその値を読み込む。"""
    # Inputs
    setting_path = Path("test/unit/setting/setting-test-load-1.yaml")
    setting_loader = SettingHandler(setting_path)
    settings = setting_loader.load()
    # Expects
    true_setting = {"allow_origin": None, "cors_policy_mode": CorsPolicyMode.localapps}
    # Outputs
    setting = _setting_adapter.dump_python(settings)
    # Test
    assert true_setting == setting


def test_setting_handler_load_exist_file_2() -> None:
    """`SettingHandler` に設定ファイルのパスを渡すとその値を読み込む。"""
    # Inputs
    setting_path = Path("test/unit/setting/setting-test-load-2.yaml")
    setting_loader = SettingHandler(setting_path)
    settings = setting_loader.load()
    # Expects
    true_setting = {"allow_origin": None, "cors_policy_mode": "all"}
    # Outputs
    setting = _setting_adapter.dump_python(settings)
    # Test
    assert true_setting == setting


def test_setting_handler_load_exist_file_3() -> None:
    """`SettingHandler` に設定ファイルのパスを渡すとその値を読み込む。"""
    # Inputs
    setting_path = Path("test/unit/setting/setting-test-load-3.yaml")
    setting_loader = SettingHandler(setting_path)
    settings = setting_loader.load()
    # Expects
    true_setting = {
        "allow_origin": "192.168.254.255 192.168.255.255",
        "cors_policy_mode": CorsPolicyMode.localapps,
    }
    # Outputs
    setting = _setting_adapter.dump_python(settings)
    # Test
    assert true_setting == setting


def test_setting_handler_save(tmp_path: Path) -> None:
    """`SettingHandler.save()` で設定値を保存できる。"""
    # Inputs
    setting_path = tmp_path / "setting-test-dump.yaml"
    setting_loader = SettingHandler(setting_path)
    new_setting = Setting(cors_policy_mode=CorsPolicyMode.localapps)
    # Expects
    true_setting = {"allow_origin": None, "cors_policy_mode": CorsPolicyMode.localapps}
    # Outputs
    setting_loader.save(new_setting)
    # NOTE: `.load()` の正常動作を前提とする
    setting = _setting_adapter.dump_python(setting_loader.load())
    # Test
    assert true_setting == setting


def test_setting_invalid_input() -> None:
    """`Setting` は不正な入力に対してエラーを送出する。"""
    # Test
    with pytest.raises(ValidationError) as _:
        Setting(cors_policy_mode="invalid_value", allow_origin="*")
