from pydantic import BaseModel, Field

from ..model import AudioQuery

class MorphingQuery(BaseModel):
    audio_query: AudioQuery = Field(title='音声合成用のクエリ')
    base_speaker: int = Field(title='ベース話者')
    target_speaker: int = Field(title='ターゲット話者')
    morph_rate: float = Field(title='ベース話者の割合', ge=0.0, le=1.0)
