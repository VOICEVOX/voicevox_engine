"""設定のモデル"""

from enum import Enum

from pydantic import BaseModel, Field


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
