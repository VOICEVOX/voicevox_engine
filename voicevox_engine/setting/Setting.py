from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class CorsPolicyMode(str, Enum):
    all = "all"
    localapps = "localapps"


class Setting(BaseModel):
    """
    エンジンの設定情報
    """

    cors_policy_mode: CorsPolicyMode = Field(title="リソース共有ポリシー")
    allow_origin: Optional[str] = Field(title="許可するオリジン")

    class Config:
        use_enum_values = True
