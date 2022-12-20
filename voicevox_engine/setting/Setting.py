from typing import Optional

from pydantic import BaseModel, Field


class Setting(BaseModel):
    """
    エンジンの設定情報
    """

    cors_policy_mode: str = Field(title="リソース共有ポリシー")
    allow_origin: Optional[str] = Field(title="許可するオリジン")
