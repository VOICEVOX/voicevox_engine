from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class SpeakerStyle(BaseModel):
    """
    スピーカーのスタイル情報
    """

    name: str = Field(title="スタイル名")
    id: int = Field(title="スタイルID")


class SpeakerSupportPermittedSynthesisMorphing(str, Enum):
    ALL = "ALL"  # 全て許可
    SELF_ONLY = "SELF_ONLY"  # 同じ話者内でのみ許可
    NOTHING = "NOTHING"  # 全て禁止

    @classmethod
    def _missing_(cls, value: object) -> "SpeakerSupportPermittedSynthesisMorphing":
        return SpeakerSupportPermittedSynthesisMorphing.ALL


class SpeakerSupportedFeatures(BaseModel):
    """
    話者の対応機能の情報
    """

    permitted_synthesis_morphing: SpeakerSupportPermittedSynthesisMorphing = Field(
        title="モーフィング機能への対応", default=SpeakerSupportPermittedSynthesisMorphing(None)
    )


class CoreSpeaker(BaseModel):
    """
    コアに含まれるスピーカー情報
    """

    name: str = Field(title="名前")
    speaker_uuid: str = Field(title="スピーカーのUUID")
    styles: List[SpeakerStyle] = Field(title="スピーカースタイルの一覧")
    version: str = Field("スピーカーのバージョン")


class EngineSpeaker(BaseModel):
    """
    エンジンに含まれるスピーカー情報
    """

    supported_features: SpeakerSupportedFeatures = Field(
        title="スピーカーの対応機能", default_factory=SpeakerSupportedFeatures
    )


class Speaker(CoreSpeaker, EngineSpeaker):
    """
    スピーカー情報
    """

    pass


class StyleInfo(BaseModel):
    """
    スタイルの追加情報
    """

    id: int = Field(title="スタイルID")
    icon: str = Field(title="当該スタイルのアイコンをbase64エンコードしたもの")
    portrait: Optional[str] = Field(title="当該スタイルのportrait.pngをbase64エンコードしたもの")
    voice_samples: List[str] = Field(title="voice_sampleのwavファイルをbase64エンコードしたもの")


class SpeakerInfo(BaseModel):
    """
    話者の追加情報
    """

    policy: str = Field(title="policy.md")
    portrait: str = Field(title="portrait.pngをbase64エンコードしたもの")
    style_infos: List[StyleInfo] = Field(title="スタイルの追加情報")
