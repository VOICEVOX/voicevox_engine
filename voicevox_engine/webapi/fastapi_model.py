from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from voicevox_engine import model, preset
from voicevox_engine.webapi import fastapi_model_converter

"""
このファイルの型はmodel.pyと重複しているように見えるが、これは内部で使用しているmodel.pyの変更をAPI定義に影響を与えないするためである。
fastapiのリクエスト、レスポンスに使用する型はmodel.pyにあるものではなく必ずここに定義してある型を使用すること。
model.pyあるいはこのファイルの型に変更がある場合fastapi_model_converterでの変換処理を実装する
"""


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

    @classmethod
    def from_model(cls, mora: model.Mora) -> Mora:
        return fastapi_model_converter.from_model_mora(mora)

    def to_model(self) -> model.Mora:
        return fastapi_model_converter.to_model_mora(self)


class AccentPhrase(BaseModel):
    """
    アクセント句ごとの情報
    """

    moras: List[Mora] = Field(title="モーラのリスト")
    accent: int = Field(title="アクセント箇所")
    pause_mora: Optional[Mora] = Field(title="後ろに無音を付けるかどうか")

    def __hash__(self):
        items = [
            (k, tuple(v)) if isinstance(v, List) else (k, v)
            for k, v in self.__dict__.items()
        ]
        return hash(tuple(sorted(items)))

    @classmethod
    def from_model(cls, accent_phrase: model.AccentPhrase) -> AccentPhrase:
        return fastapi_model_converter.from_model_accent_phrase(accent_phrase)

    def to_model(self) -> model.AccentPhrase:
        return fastapi_model_converter.to_model_accent_phrase(self)


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

    @classmethod
    def from_model(cls, audio_query: model.AudioQuery) -> AudioQuery:
        return fastapi_model_converter.from_model_audio_query(audio_query)

    def to_model(self) -> model.AudioQuery:
        return fastapi_model_converter.to_model_audio_query(self)


class ParseKanaBadRequest(BaseModel):
    text: str = Field(title="エラーメッセージ")
    error_name: str = Field(
        title="エラー名",
        description="|name|description|\n|---|---|\n"
        + "\n".join(
            [
                "| {} | {} |".format(err.name, err.value)
                for err in list(model.ParseKanaErrorCode)
            ]
        ),
    )
    error_args: Dict[str, str] = Field(title="エラーを起こした箇所")

    def __init__(self, err: model.ParseKanaError):
        super().__init__(text=err.text, error_name=err.errname, error_args=err.kwargs)


class SpeakerStyle(BaseModel):
    """
    スピーカーのスタイル情報
    """

    name: str = Field(title="スタイル名")
    id: int = Field(title="スタイルID")

    @classmethod
    def from_model(cls, speaker_style: model.SpeakerStyle) -> SpeakerStyle:
        return fastapi_model_converter.from_model_speaker_style(speaker_style)

    def to_model(self) -> model.SpeakerStyle:
        return fastapi_model_converter.to_model_speaker_style(self)


class Speaker(BaseModel):
    """
    スピーカー情報
    """

    name: str = Field(title="名前")
    speaker_uuid: str = Field(title="スピーカーのUUID")
    styles: List[SpeakerStyle] = Field(title="スピーカースタイルの一覧")
    version: str = Field("スピーカーのバージョン")

    @classmethod
    def from_model(cls, speaker: model.Speaker) -> Speaker:
        return fastapi_model_converter.from_model_speaker(speaker)

    def to_model(self) -> model.Speaker:
        return fastapi_model_converter.to_model_speaker(self)


class StyleInfo(BaseModel):
    """
    スタイルの追加情報
    """

    id: int = Field(title="スタイルID")
    icon: str = Field(title="当該スタイルのアイコンをbase64エンコードしたもの")
    voice_samples: List[str] = Field(title="voice_sampleのwavファイルをbase64エンコードしたもの")

    @classmethod
    def from_model(cls, style_info: model.StyleInfo) -> StyleInfo:
        return fastapi_model_converter.from_model_style_info(style_info)

    def to_model(self) -> model.StyleInfo:
        return fastapi_model_converter.to_model_style_info(self)


class SpeakerInfo(BaseModel):
    """
    話者の追加情報
    """

    policy: str = Field(title="policy.md")
    portrait: str = Field(title="portrait.pngをbase64エンコードしたもの")
    style_infos: List[StyleInfo] = Field(title="スタイルの追加情報")

    @classmethod
    def from_model(cls, speaker_info: model.SpeakerInfo) -> SpeakerInfo:
        return fastapi_model_converter.from_model_speaker_info(speaker_info)

    def to_model(self) -> model.SpeakerInfo:
        return fastapi_model_converter.to_model_speaker_info(self)


class Preset(BaseModel):
    """
    プリセット情報
    """

    id: int = Field(title="プリセットID")
    name: str = Field(title="プリセット名")
    speaker_uuid: str = Field(title="スピーカーのUUID")
    style_id: int = Field(title="スタイルID")
    speedScale: float = Field(title="全体の話速")
    pitchScale: float = Field(title="全体の音高")
    intonationScale: float = Field(title="全体の抑揚")
    volumeScale: float = Field(title="全体の音量")
    prePhonemeLength: float = Field(title="音声の前の無音時間")
    postPhonemeLength: float = Field(title="音声の後の無音時間")

    @classmethod
    def from_model(cls, preset: preset.Preset) -> Preset:
        return fastapi_model_converter.from_model_preset(preset)

    def to_model(self) -> preset.Preset:
        return fastapi_model_converter.to_model_preset(self)
