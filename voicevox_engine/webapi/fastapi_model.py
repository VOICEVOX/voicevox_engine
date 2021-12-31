from __future__ import annotations

import copy
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from voicevox_engine import model, preset

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
    def from_engine(cls, mora: model.Mora) -> Mora:
        return cls(
            text=mora.text,
            consonant=mora.consonant,
            consonant_length=mora.consonant_length,
            vowel=mora.vowel,
            vowel_length=mora.vowel_length,
            pitch=mora.pitch,
        )

    def to_engine(self) -> model.Mora:
        return model.Mora(
            text=self.text,
            consonant=self.consonant,
            consonant_length=self.consonant_length,
            vowel=self.vowel,
            vowel_length=self.vowel_length,
            pitch=self.pitch,
        )


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
    def from_engine(cls, accent_phrase: model.AccentPhrase) -> AccentPhrase:
        return cls(
            moras=[Mora.from_engine(mora) for mora in accent_phrase.moras],
            accent=accent_phrase.accent,
            pause_mora=Mora.from_engine(accent_phrase.pause_mora)
            if accent_phrase.pause_mora is not None
            else None,
        )

    def to_engine(self) -> model.AccentPhrase:
        return model.AccentPhrase(
            moras=[mora.to_engine() for mora in self.moras],
            accent=self.accent,
            pause_mora=self.pause_mora.to_engine()
            if self.pause_mora is not None
            else None,
        )


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
    def from_engine(cls, audio_query: model.AudioQuery) -> AudioQuery:
        return cls(
            accent_phrases=[
                AccentPhrase.from_engine(accent_phrase)
                for accent_phrase in audio_query.accent_phrases
            ],
            speedScale=audio_query.speedScale,
            pitchScale=audio_query.pitchScale,
            intonationScale=audio_query.intonationScale,
            volumeScale=audio_query.volumeScale,
            prePhonemeLength=audio_query.prePhonemeLength,
            postPhonemeLength=audio_query.postPhonemeLength,
            outputSamplingRate=audio_query.outputSamplingRate,
            outputStereo=audio_query.outputStereo,
            kana=audio_query.kana,
        )

    def to_engine(self) -> model.AudioQuery:
        return model.AudioQuery(
            accent_phrases=[
                accent_phrase.to_engine() for accent_phrase in self.accent_phrases
            ],
            speedScale=self.speedScale,
            pitchScale=self.pitchScale,
            intonationScale=self.intonationScale,
            volumeScale=self.volumeScale,
            prePhonemeLength=self.prePhonemeLength,
            postPhonemeLength=self.postPhonemeLength,
            outputSamplingRate=self.outputSamplingRate,
            outputStereo=self.outputStereo,
            kana=self.kana,
        )


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
    def from_engine(cls, speaker_style: model.SpeakerStyle) -> SpeakerStyle:
        return cls(
            name=speaker_style.name,
            id=speaker_style.id,
        )

    def to_engine(self) -> model.SpeakerStyle:
        return model.SpeakerStyle(
            name=self.name,
            id=self.id,
        )


class Speaker(BaseModel):
    """
    スピーカー情報
    """

    name: str = Field(title="名前")
    speaker_uuid: str = Field(title="スピーカーのUUID")
    styles: List[SpeakerStyle] = Field(title="スピーカースタイルの一覧")
    version: str = Field("スピーカーのバージョン")

    @classmethod
    def from_engine(cls, speaker: model.Speaker) -> Speaker:
        return cls(
            name=speaker.name,
            speaker_uuid=speaker.speaker_uuid,
            styles=speaker.styles,
            version=speaker.version,
        )

    def to_engine(self) -> model.Speaker:
        return model.Speaker(
            name=self.name,
            speaker_uuid=self.speaker_uuid,
            styles=self.styles,
            version=self.version,
        )


class StyleInfo(BaseModel):
    """
    スタイルの追加情報
    """

    id: int = Field(title="スタイルID")
    icon: str = Field(title="当該スタイルのアイコンをbase64エンコードしたもの")
    voice_samples: List[str] = Field(title="voice_sampleのwavファイルをbase64エンコードしたもの")

    @classmethod
    def from_engine(cls, style_info: model.StyleInfo) -> StyleInfo:
        return cls(
            id=style_info.id,
            icon=style_info.icon,
            voice_samples=copy.deepcopy(style_info.voice_samples),
        )

    def to_engine(self) -> model.StyleInfo:
        return model.StyleInfo(
            id=self.id,
            icon=self.icon,
            voice_samples=copy.deepcopy(self.voice_samples),
        )


class SpeakerInfo(BaseModel):
    """
    話者の追加情報
    """

    policy: str = Field(title="policy.md")
    portrait: str = Field(title="portrait.pngをbase64エンコードしたもの")
    style_infos: List[StyleInfo] = Field(title="スタイルの追加情報")

    @classmethod
    def from_engine(cls, speaker_info: model.SpeakerInfo) -> SpeakerInfo:
        return cls(
            policy=speaker_info.policy,
            portrait=speaker_info.portrait,
            style_infos=speaker_info.style_infos,
        )

    def to_engine(self) -> model.SpeakerInfo:
        return model.SpeakerInfo(
            policy=self.policy,
            portrait=self.portrait,
            style_infos=self.style_infos,
        )


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
    def from_engine(cls, preset: preset.Preset) -> Preset:
        return cls(
            id=preset.id,
            name=preset.name,
            speaker_uuid=preset.speaker_uuid,
            style_id=preset.style_id,
            speedScale=preset.speedScale,
            pitchScale=preset.pitchScale,
            intonationScale=preset.intonationScale,
            volumeScale=preset.volumeScale,
            prePhonemeLength=preset.prePhonemeLength,
            postPhonemeLength=preset.postPhonemeLength,
        )

    def to_engine(self) -> preset.Preset:
        return preset.Preset(
            id=self.id,
            name=self.name,
            speaker_uuid=self.speaker_uuid,
            style_id=self.style_id,
            speedScale=self.speedScale,
            pitchScale=self.pitchScale,
            intonationScale=self.intonationScale,
            volumeScale=self.volumeScale,
            prePhonemeLength=self.prePhonemeLength,
            postPhonemeLength=self.postPhonemeLength,
        )
