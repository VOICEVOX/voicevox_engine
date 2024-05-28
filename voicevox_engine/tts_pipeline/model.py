"""
音声合成機能に関して API と ENGINE 内部実装が共有するモデル
「API と ENGINE 内部実装が共有するモデル」については `voicevox_engine/model.py` の module docstring を確認すること。
"""

from enum import Enum

from pydantic import BaseModel, Field


class Mora(BaseModel):
    """
    モーラ（子音＋母音）ごとの情報
    """

    text: str = Field(title="文字")
    consonant: str | None = Field(title="子音の音素")
    consonant_length: float | None = Field(title="子音の音長")
    vowel: str = Field(title="母音の音素")
    vowel_length: float = Field(title="母音の音長")
    pitch: float = Field(
        title="音高"
    )  # デフォルト値をつけるとts側のOpenAPIで生成されたコードの型がOptionalになる

    def __hash__(self) -> int:
        items = [
            (k, tuple(v)) if isinstance(v, list) else (k, v)
            for k, v in self.__dict__.items()
        ]
        return hash(tuple(sorted(items)))

    class Config:
        validate_assignment = True


class AccentPhrase(BaseModel):
    """
    アクセント句ごとの情報
    """

    moras: list[Mora] = Field(title="モーラのリスト")
    accent: int = Field(title="アクセント箇所")
    pause_mora: Mora | None = Field(title="後ろに無音を付けるかどうか")
    is_interrogative: bool = Field(default=False, title="疑問系かどうか")

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

    key: int | None = Field(title="音階")
    frame_length: int = Field(title="音符のフレーム長")
    lyric: str = Field(title="音符の歌詞")


class Score(BaseModel):
    """
    楽譜情報
    """

    notes: list[Note] = Field(title="音符のリスト")


class FramePhoneme(BaseModel):
    """
    音素の情報
    """

    phoneme: str = Field(title="音素")
    frame_length: int = Field(title="音素のフレーム長")


class FrameAudioQuery(BaseModel):
    """
    フレームごとの音声合成用のクエリ
    """

    f0: list[float] = Field(title="フレームごとの基本周波数")
    volume: list[float] = Field(title="フレームごとの音量")
    phonemes: list[FramePhoneme] = Field(title="音素のリスト")
    volumeScale: float = Field(title="全体の音量")
    outputSamplingRate: int = Field(title="音声データの出力サンプリングレート")
    outputStereo: bool = Field(title="音声データをステレオ出力するか否か")


class ParseKanaErrorCode(Enum):
    UNKNOWN_TEXT = "判別できない読み仮名があります: {text}"
    ACCENT_TOP = "句頭にアクセントは置けません: {text}"
    ACCENT_TWICE = "1つのアクセント句に二つ以上のアクセントは置けません: {text}"
    ACCENT_NOTFOUND = "アクセントを指定していないアクセント句があります: {text}"
    EMPTY_PHRASE = "{position}番目のアクセント句が空白です"
    INTERROGATION_MARK_NOT_AT_END = "アクセント句末以外に「？」は置けません: {text}"
    INFINITE_LOOP = "処理時に無限ループになってしまいました...バグ報告をお願いします。"
