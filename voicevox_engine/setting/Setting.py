from enum import Enum
from typing import Optional

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
    allow_origin: Optional[str] = Field(title="許可するオリジン")

    class Config:
        use_enum_values = True
