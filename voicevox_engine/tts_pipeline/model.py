"""
音声合成機能に関して API と ENGINE 内部実装が共有するモデル（データ構造）

モデルの注意点は `voicevox_engine/model.py` の module docstring を確認すること。
"""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field
from pydantic.json_schema import SkipJsonSchema


class Mora(BaseModel):
    """
    モーラ（子音＋母音）ごとの情報
    """

    model_config = ConfigDict(validate_assignment=True)

    text: str = Field(description="文字")
    consonant: str | SkipJsonSchema[None] = Field(
        default=None, description="子音の音素"
    )
    consonant_length: float | SkipJsonSchema[None] = Field(
        default=None, description="子音の音長"
    )
    vowel: str = Field(description="母音の音素")
    vowel_length: float = Field(description="母音の音長")
    pitch: float = Field(
        description="音高"
    )  # デフォルト値をつけるとts側のOpenAPIで生成されたコードの型がOptionalになる

    def __hash__(self) -> int:
        items = [
            (k, tuple(v)) if isinstance(v, list) else (k, v)
            for k, v in self.__dict__.items()
        ]
        return hash(tuple(sorted(items)))


class AccentPhrase(BaseModel):
    """
    アクセント句ごとの情報
    """

    moras: list[Mora] = Field(description="モーラのリスト")
    accent: int = Field(description="アクセント箇所")
    pause_mora: Mora | SkipJsonSchema[None] = Field(
        default=None, description="後ろに無音を付けるかどうか"
    )
    is_interrogative: bool = Field(default=False, description="疑問系かどうか")

    def __hash__(self) -> int:
        items = [
            (k, tuple(v)) if isinstance(v, list) else (k, v)
            for k, v in self.__dict__.items()
        ]
        return hash(tuple(sorted(items)))


class Note(BaseModel):
    """
    音符ごとの情報
    """

    key: int | SkipJsonSchema[None] = Field(default=None, description="音階")
    frame_length: int = Field(description="音符のフレーム長")
    lyric: str = Field(description="音符の歌詞")


class Score(BaseModel):
    """
    楽譜情報
    """

    notes: list[Note] = Field(description="音符のリスト")


class FramePhoneme(BaseModel):
    """
    音素の情報
    """

    phoneme: str = Field(description="音素")
    frame_length: int = Field(description="音素のフレーム長")


class FrameAudioQuery(BaseModel):
    """
    フレームごとの音声合成用のクエリ
    """

    f0: list[float] = Field(description="フレームごとの基本周波数")
    volume: list[float] = Field(description="フレームごとの音量")
    phonemes: list[FramePhoneme] = Field(description="音素のリスト")
    volumeScale: float = Field(description="全体の音量")
    outputSamplingRate: int = Field(description="音声データの出力サンプリングレート")
    outputStereo: bool = Field(description="音声データをステレオ出力するか否か")


class ParseKanaErrorCode(Enum):
    UNKNOWN_TEXT = "判別できない読み仮名があります: {text}"
    ACCENT_TOP = "句頭にアクセントは置けません: {text}"
    ACCENT_TWICE = "1つのアクセント句に二つ以上のアクセントは置けません: {text}"
    ACCENT_NOTFOUND = "アクセントを指定していないアクセント句があります: {text}"
    EMPTY_PHRASE = "{position}番目のアクセント句が空白です"
    INTERROGATION_MARK_NOT_AT_END = "アクセント句末以外に「？」は置けません: {text}"
    INFINITE_LOOP = "処理時に無限ループになってしまいました...バグ報告をお願いします。"
