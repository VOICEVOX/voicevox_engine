from typing import Dict, List, Optional
from enum import Enum

from pydantic import BaseModel, Field


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
    speedScale: float = Field(title="全体の話速")
    pitchScale: float = Field(title="全体の音高")
    intonationScale: float = Field(title="全体の抑揚")
    volumeScale: float = Field(title="全体の音量")
    prePhonemeLength: float = Field(title="音声の前の無音時間")
    postPhonemeLength: float = Field(title="音声の後の無音時間")
    outputSamplingRate: int = Field(title="音声データの出力サンプリングレート")
    outputStereo: bool = Field(title="音声データをステレオ出力するか否か")
    kana: Optional[str] = Field(title="[読み取り専用]Softalkライクな読み仮名。音声合成クエリとしては無視される")


class ParseKanaErrorCode(Enum):
    UNKNOWN_TEXT = "判別できない読み仮名があります: {text}"
    ACCENT_TOP = "句頭にアクセントは置けません: {text}"
    ACCENT_TWICE = "1つのアクセント句に二つ以上のアクセントは置けません: {text}"
    ACCENT_NOTFOUND = "アクセントを指定していないアクセント句があります: {text}"
    EMPTY_PHRASE = "{position}番目のアクセント句が空白です"
    INFINITE_LOOP = "処理時に無限ループになってしまいました...バグ報告をお願いします。"

class ParseKanaError(Exception):
    def __init__(self, errcode: ParseKanaErrorCode, **kwargs):
        self.errcode = errcode.name
        self.kwargs: Dict[str, str] = kwargs
        err_fmt: str = errcode.value
        self.text = err_fmt.format(**kwargs)

class AudioQueryBadRequest(BaseModel):
    text: str = Field(title="エラーメッセージ")
    error_code: str = Field(title="エラーコード", description="|name|description|\n|---|---|\n" + "\n".join(
        ["| {} | {} |".format(err.name, err.value) for err in list(ParseKanaErrorCode)]
    ))
    error_args: Dict[str, str] = Field(title="エラーを起こした箇所")
    def __init__(self, err: ParseKanaError):
        super().__init__(
            text=err.text,
            error_code=err.errcode,
            error_args=err.kwargs
        )


class Speaker(BaseModel):
    """
    スピーカー情報
    """

    name: str = Field(title="名前")
    speaker_id: int = Field(title="スピーカーID")
