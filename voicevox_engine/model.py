from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

"""
ここで定義されている型は内部で使用するための型であり、API定義を変更したければvoicevox_engine/webapi/fastapi_model.pyの定義を変更すること。
また、対応する型との適切な変換処理を実装すること
"""

# FIXME: このファイルの各型からpydantic由来の機能を削除し、dataclassにする。もともとmodel.pyはAPI定義に使用されていたが、
# 使用するデータ型が分離したため


class Mora(BaseModel):
    """
    モーラ（子音＋母音）ごとの情報
    """

    text: str = Field(title="文字")
    consonant: Optional[str] = Field(title="子音の音素")
    consonant_length: Optional[float] = Field(title="子音の音長")
    vowel: str = Field(title="母音の音素")
    vowel_length: float = Field(title="母音の音長")
    pitch: float = Field(title="音高")  # デフォルト値をつけるとts側のOpenAPIで生成されたコードの型がOptionalになる

    def __hash__(self):
        items = [
            (k, tuple(v)) if isinstance(v, List) else (k, v)
            for k, v in self.__dict__.items()
        ]
        return hash(tuple(sorted(items)))


class AccentPhrase(BaseModel):
    """
    アクセント句ごとの情報
    """

    moras: List[Mora] = Field(title="モーラのリスト")
    accent: int = Field(title="アクセント箇所")
    pause_mora: Optional[Mora] = Field(title="後ろに無音を付けるかどうか")
    is_interrogative: bool

    def __hash__(self):
        items = [
            (k, tuple(v)) if isinstance(v, List) else (k, v)
            for k, v in self.__dict__.items()
        ]
        return hash(tuple(sorted(items)))


class AudioQuery(BaseModel):
    """
    音声合成用のクエリ
    """

    accent_phrases: List[AccentPhrase] = Field(title="アクセント句のリスト")
    speedScale: float = Field(title="全体の話速")
    pitchScale: float = Field(title="全体の音高")
    intonationScale: float = Field(title="全体の抑揚")
    volumeScale: float = Field(title="全体の音量")
    prePhonemeLength: float = Field(title="音声の前の無音時間")
    postPhonemeLength: float = Field(title="音声の後の無音時間")
    outputSamplingRate: int = Field(title="音声データの出力サンプリングレート")
    outputStereo: bool = Field(title="音声データをステレオ出力するか否か")
    kana: Optional[str] = Field(title="[読み取り専用]AquesTalkライクな読み仮名。音声合成クエリとしては無視される")

    def __hash__(self):
        items = [
            (k, tuple(v)) if isinstance(v, List) else (k, v)
            for k, v in self.__dict__.items()
        ]
        return hash(tuple(sorted(items)))


class ParseKanaErrorCode(Enum):
    UNKNOWN_TEXT = "判別できない読み仮名があります: {text}"
    ACCENT_TOP = "句頭にアクセントは置けません: {text}"
    ACCENT_TWICE = "1つのアクセント句に二つ以上のアクセントは置けません: {text}"
    ACCENT_NOTFOUND = "アクセントを指定していないアクセント句があります: {text}"
    EMPTY_PHRASE = "{position}番目のアクセント句が空白です"
    INFINITE_LOOP = "処理時に無限ループになってしまいました...バグ報告をお願いします。"


class ParseKanaError(Exception):
    def __init__(self, errcode: ParseKanaErrorCode, **kwargs):
        self.errcode = errcode
        self.errname = errcode.name
        self.kwargs: Dict[str, str] = kwargs
        err_fmt: str = errcode.value
        self.text = err_fmt.format(**kwargs)


class SpeakerStyle(BaseModel):
    """
    スピーカーのスタイル情報
    """

    name: str = Field(title="スタイル名")
    id: int = Field(title="スタイルID")


class Speaker(BaseModel):
    """
    スピーカー情報
    """

    name: str = Field(title="名前")
    speaker_uuid: str = Field(title="スピーカーのUUID")
    styles: List[SpeakerStyle] = Field(title="スピーカースタイルの一覧")
    version: str = Field("スピーカーのバージョン")


class StyleInfo(BaseModel):
    """
    スタイルの追加情報
    """

    id: int = Field(title="スタイルID")
    icon: str = Field(title="当該スタイルのアイコンをbase64エンコードしたもの")
    voice_samples: List[str] = Field(title="voice_sampleのwavファイルをbase64エンコードしたもの")


class SpeakerInfo(BaseModel):
    """
    話者の追加情報
    """

    policy: str = Field(title="policy.md")
    portrait: str = Field(title="portrait.pngをbase64エンコードしたもの")
    style_infos: List[StyleInfo] = Field(title="スタイルの追加情報")
