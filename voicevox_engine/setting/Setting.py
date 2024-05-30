from enum import Enum
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from ..utility.path_utility import get_save_dir


class CorsPolicyMode(str, Enum):
    """
    CORSの許可モード
    """

    all = "all"  # 全てのオリジンからのリクエストを許可
    localapps = "localapps"  # ローカルアプリケーションからのリクエストを許可


class Setting(BaseModel):
    """
    エンジンの設定情報
    """

    cors_policy_mode: CorsPolicyMode = Field(title="リソース共有ポリシー")
    allow_origin: str | None = Field(title="許可するオリジン")


USER_SETTING_PATH: Path = get_save_dir() / "setting.yml"


class SettingHandler:
    def __init__(self, setting_file_path: Path) -> None:
        """
        設定ファイルの管理
        Parameters
        ----------
        setting_file_path : Path
            設定ファイルのパス。存在しない場合はデフォルト値を設定。
        """
        self.setting_file_path = setting_file_path

    def load(self) -> Setting:
        """設定値をファイルから読み込む。"""
        if not self.setting_file_path.is_file():
            # 設定ファイルが存在しないためデフォルト値を取得
            setting = {"allow_origin": None, "cors_policy_mode": "localapps"}
        else:
            # 指定された設定ファイルから値を取得
            # FIXME: 型チェックと例外処理を追加する
            setting = yaml.safe_load(self.setting_file_path.read_text(encoding="utf-8"))

        return Setting(
            cors_policy_mode=setting["cors_policy_mode"],
            allow_origin=setting["allow_origin"],
        )

    def save(self, settings: Setting) -> None:
        """設定値をファイルへ書き込む。"""
        settings_dict = settings.dict()

        if isinstance(settings_dict["cors_policy_mode"], Enum):
            settings_dict["cors_policy_mode"] = settings_dict["cors_policy_mode"].value

        with open(self.setting_file_path, mode="w", encoding="utf-8") as f:
            yaml.safe_dump(settings_dict, f)
