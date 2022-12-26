from pathlib import Path

from ..utility import engine_root, get_save_dir
from .SettingLoader import SettingLoader

DEFAULT_SETTING_PATH: Path = engine_root() / "default_setting.yml"
USER_SETTING_PATH: Path = get_save_dir() / "setting.yml"


def setup_setting_file() -> None:
    default_setting = SettingLoader(DEFAULT_SETTING_PATH).load_setting_file()

    # 設定を永続化させる
    if not USER_SETTING_PATH.is_file():
        SettingLoader(USER_SETTING_PATH).dump_setting_file(default_setting)
