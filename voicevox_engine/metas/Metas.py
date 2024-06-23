"""キャラクター情報とキャラクターメタ情報"""

from enum import Enum
from typing import Literal, NewType

from pydantic import BaseModel, Field
from pydantic.json_schema import SkipJsonSchema

# NOTE: 循環importを防ぐためにとりあえずここに書いている
# FIXME: 他のmodelに依存せず、全modelから参照できる場所に配置する
StyleId = NewType("StyleId", int)
StyleType = Literal["talk", "singing_teacher", "frame_decode", "sing"]


class SpeakerStyle(BaseModel):
    """キャラクターのスタイル情報"""

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


class SpeakerSupportPermittedSynthesisMorphing(str, Enum):
    ALL = "ALL"  # 全て許可
    SELF_ONLY = "SELF_ONLY"  # 同じキャラクター内でのみ許可
    NOTHING = "NOTHING"  # 全て禁止


class SpeakerSupportedFeatures(BaseModel):
    """キャラクターの対応機能の情報"""

    permitted_synthesis_morphing: SpeakerSupportPermittedSynthesisMorphing = Field(
        title="モーフィング機能への対応",
        default=SpeakerSupportPermittedSynthesisMorphing.ALL,
    )


class Speaker(BaseModel):
    """キャラクター情報"""

    name: str = Field(title="名前")
    speaker_uuid: str = Field(title="キャラクターのUUID")
    styles: list[SpeakerStyle] = Field(title="スタイルの一覧")
    version: str = Field(title="キャラクターのバージョン")
    supported_features: SpeakerSupportedFeatures = Field(
        title="キャラクターの対応機能", default_factory=SpeakerSupportedFeatures
    )


class StyleInfo(BaseModel):
    """スタイルの追加情報"""

    id: StyleId = Field(title="スタイルID")
    icon: str = Field(
        title="このスタイルのアイコンをbase64エンコードしたもの、あるいはURL"
    )
    portrait: str | SkipJsonSchema[None] = Field(
        default=None,
        title="このスタイルの立ち絵画像をbase64エンコードしたもの、あるいはURL",
    )
    voice_samples: list[str] = Field(
        title="サンプル音声をbase64エンコードしたもの、あるいはURL"
    )


class SpeakerInfo(BaseModel):
    """キャラクターの追加情報"""

    policy: str = Field(title="policy.md")
    portrait: str = Field(title="立ち絵画像をbase64エンコードしたもの、あるいはURL")
    style_infos: list[StyleInfo] = Field(title="スタイルの追加情報")
