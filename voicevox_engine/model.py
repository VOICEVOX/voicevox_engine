from typing import List, Optional

from pydantic import BaseModel, Field


class Mora(BaseModel):
    """
    モーラ（子音＋母音）ごとの情報
    """

    text: str = Field(title="文字")
    consonant: Optional[str] = Field(title="子音の音素")
    vowel: str = Field(title="母音の音素")
    pitch: float = Field(title="音高")


class AccentPhrase(BaseModel):
    """
    アクセント句ごとの情報
    """

    moras: List[Mora] = Field(title="モーラのリスト")
    accent: int = Field(title="アクセント箇所")
    pause_mora: Optional[Mora] = Field(title="後ろに無音を付けるかどうか")


class AudioQuery(BaseModel):
    """
    音声合成用のクエリ
    """

    accent_phrases: List[AccentPhrase] = Field(title="アクセント句のリスト")
    speedScale: float = Field(1, title="全体の話速")
    pitchScale: float = Field(0, title="全体の音高")
    intonationScale: float = Field(1, title="全体の抑揚")
