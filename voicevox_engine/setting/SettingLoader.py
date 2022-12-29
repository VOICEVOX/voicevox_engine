from pathlib import Path

import yaml

from ..utility import engine_root, get_save_dir
from .Setting import Setting

DEFAULT_SETTING_PATH: Path = engine_root() / "default_setting.yml"
USER_SETTING_PATH: Path = get_save_dir() / "setting.yml"


class SettingLoader:
    def __init__(self, setting_file_path: Path) -> None:
        self.setting_file_path = setting_file_path

    def load_setting_file(self) -> Setting:
        if not self.setting_file_path.is_file():
            setting = yaml.safe_load(DEFAULT_SETTING_PATH.read_text(encoding="utf-8"))
        else:
            setting = yaml.safe_load(self.setting_file_path.read_text(encoding="utf-8"))

        setting = Setting(
            cors_policy_mode=setting["cors_policy_mode"],
            allow_origin=setting["allow_origin"],
        )

        return setting

    def dump_setting_file(self, settings: Setting) -> None:
        settings_dict = settings.dict()

        with open(self.setting_file_path, mode="w", encoding="utf-8") as f:
            yaml.safe_dump(settings_dict, f)
