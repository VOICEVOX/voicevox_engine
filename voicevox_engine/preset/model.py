"""
プリセット機能に関して API と ENGINE 内部実装が共有するモデル（データ構造）

モデルの注意点は `voicevox_engine/model.py` の module docstring を確認すること。
"""

from pydantic import BaseModel, Field
from pydantic.json_schema import SkipJsonSchema

from voicevox_engine.metas.Metas import StyleId


class Preset(BaseModel):
    """
    プリセット情報
    """

    id: int = Field(description="プリセットID")
    name: str = Field(description="プリセット名")
    speaker_uuid: str = Field(description="キャラクターのUUID")
    style_id: StyleId = Field(description="スタイルID")
    speedScale: float = Field(description="全体の話速")
    pitchScale: float = Field(description="全体の音高")
    intonationScale: float = Field(description="全体の抑揚")
    volumeScale: float = Field(description="全体の音量")
    prePhonemeLength: float = Field(description="音声の前の無音時間")
    postPhonemeLength: float = Field(description="音声の後の無音時間")
    pauseLength: float | SkipJsonSchema[None] = Field(
        default=None, description="句読点などの無音時間"
    )
    pauseLengthScale: float = Field(
        default=1, description="句読点などの無音時間（倍率）"
    )
