from enum import Enum
from typing import List, Literal, NewType, Optional

from pydantic import BaseModel, Field

# NOTE: 循環importを防ぐためにとりあえずここに書いている
# FIXME: 他のmodelに依存せず、全modelから参照できる場所に配置する
StyleId = NewType("StyleId", int)
StyleType = Literal["talk", "singing_teacher", "frame_decode", "sing"]


class SpeakerStyle(BaseModel):
    """
    話者のスタイル情報
    """

    name: str = Field(title="スタイル名")
    id: StyleId = Field(title="スタイルID")
    type: Optional[StyleType] = Field(
        default="talk",
        title=(
            "スタイルの種類。"
            "talk:音声合成クエリの作成と音声合成が可能。"
            "singing_teacher:歌唱音声合成用のクエリの作成が可能。"
            "frame_decode:歌唱音声合成が可能。"
            "sing:歌唱音声合成用のクエリの作成と歌唱音声合成が可能。"
        ),
    )


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
        title="モーフィング機能への対応",
        default=SpeakerSupportPermittedSynthesisMorphing(None),
    )


class CoreSpeaker(BaseModel):
    """
    コアに含まれる話者情報
    """

    name: str = Field(title="名前")
    speaker_uuid: str = Field(title="話者のUUID")
    styles: List[SpeakerStyle] = Field(title="スタイルの一覧")
    version: str = Field("話者のバージョン")


class EngineSpeaker(BaseModel):
    """
    エンジンに含まれる話者情報
    """

    supported_features: SpeakerSupportedFeatures = Field(
        title="話者の対応機能", default_factory=SpeakerSupportedFeatures
    )


class Speaker(CoreSpeaker, EngineSpeaker):
    """
    話者情報
    """

    pass


class StyleInfo(BaseModel):
    """
    スタイルの追加情報
    """

    id: StyleId = Field(title="スタイルID")
    icon: str = Field(title="当該スタイルのアイコンをbase64エンコードしたもの")
    portrait: Optional[str] = Field(
        title="当該スタイルのportrait.pngをbase64エンコードしたもの"
    )
    voice_samples: List[str] = Field(
        title="voice_sampleのwavファイルをbase64エンコードしたもの"
    )


class SpeakerInfo(BaseModel):
    """
    話者の追加情報
    """

    policy: str = Field(title="policy.md")
    portrait: str = Field(title="portrait.pngをbase64エンコードしたもの")
    style_infos: List[StyleInfo] = Field(title="スタイルの追加情報")
