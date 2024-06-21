"""話者情報と話者メタ情報"""

from typing import Literal, NewType

from pydantic import BaseModel, Field
from pydantic.json_schema import SkipJsonSchema

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
    type: StyleType = Field(
        default="talk",
        title=(
            "スタイルの種類。"
            "talk:音声合成クエリの作成と音声合成が可能。"
            "singing_teacher:歌唱音声合成用のクエリの作成が可能。"
            "frame_decode:歌唱音声合成が可能。"
            "sing:歌唱音声合成用のクエリの作成と歌唱音声合成が可能。"
        ),
    )


class SpeakerSupportedFeatures(BaseModel):
    """
    話者の対応機能の情報
    """

    # 全て許可, 同じ話者内でのみ許可, 全て禁止
    permitted_synthesis_morphing: Literal["ALL", "SELF_ONLY", "NOTHING"] = Field(
        title="モーフィング機能への対応",
        default="ALL",
    )


class Speaker(BaseModel):
    """
    話者情報
    """

    name: str = Field(title="名前")
    speaker_uuid: str = Field(title="話者のUUID")
    styles: list[SpeakerStyle] = Field(title="スタイルの一覧")
    version: str = Field(title="話者のバージョン")
    supported_features: SpeakerSupportedFeatures = Field(
        title="話者の対応機能", default_factory=SpeakerSupportedFeatures
    )


class StyleInfo(BaseModel):
    """
    スタイルの追加情報
    """

    id: StyleId = Field(title="スタイルID")
    icon: str = Field(title="当該スタイルのアイコンをbase64エンコードしたもの")
    portrait: str | SkipJsonSchema[None] = Field(
        default=None, title="当該スタイルのportrait.pngをbase64エンコードしたもの"
    )
    voice_samples: list[str] = Field(
        title="voice_sampleのwavファイルをbase64エンコードしたもの"
    )


class SpeakerInfo(BaseModel):
    """
    話者の追加情報
    """

    policy: str = Field(title="policy.md")
    portrait: str = Field(title="portrait.pngをbase64エンコードしたもの")
    style_infos: list[StyleInfo] = Field(title="スタイルの追加情報")
