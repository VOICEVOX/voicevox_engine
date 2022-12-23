from pathlib import Path

import yaml

from .Setting import Setting


class SettingLoader:
    def __init__(self, setting_file_path: Path) -> None:
        self.setting_file_path = setting_file_path

    def load_setting_file(self) -> Setting:
        setting = yaml.safe_load(self.setting_file_path.read_text(encoding="utf-8"))

        setting = Setting(
            cors_policy_mode=setting["cors_policy_mode"],
            allow_origin=setting["allow_origin"],
        )

        return setting

    def dump_setting_file(self, settings: Setting) -> None:
        settings_dict = settings.dict()

        with open("setting.yml", mode="w", encoding="utf-8") as f:
            yaml.dump(settings_dict, f)
