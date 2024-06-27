"""
モーフィング機能に関して API と ENGINE 内部実装が共有するモデル（データ構造）

モデルの注意点は `voicevox_engine/model.py` の module docstring を確認すること。
"""

from pydantic import BaseModel, Field


class MorphableTargetInfo(BaseModel):
    is_morphable: bool = Field(
        description="指定したキャラクターに対してモーフィングの可否"
    )
    # FIXME: add reason property
    # reason: str | None = Field(description="is_morphableがfalseである場合、その理由")
