from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, StrictStr

from .metas.Metas import Speaker, SpeakerInfo


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


class AudioQuery(BaseModel):
    """
    音声合成用のクエリ
    """

    accent_phrases: list[AccentPhrase] = Field(title="アクセント句のリスト")
    speedScale: float = Field(title="全体の話速")
    pitchScale: float = Field(title="全体の音高")
    intonationScale: float = Field(title="全体の抑揚")
    volumeScale: float = Field(title="全体の音量")
    prePhonemeLength: float = Field(title="音声の前の無音時間")
    postPhonemeLength: float = Field(title="音声の後の無音時間")
    outputSamplingRate: int = Field(title="音声データの出力サンプリングレート")
    outputStereo: bool = Field(title="音声データをステレオ出力するか否か")
    kana: str | None = Field(
        title="[読み取り専用]AquesTalk 風記法によるテキスト。音声合成用のクエリとしては無視される"
    )

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


class ParseKanaError(Exception):
    def __init__(self, errcode: ParseKanaErrorCode, **kwargs: Any) -> None:
        self.errcode = errcode
        self.errname = errcode.name
        self.kwargs = kwargs
        err_fmt: str = errcode.value
        self.text = err_fmt.format(**kwargs)


class ParseKanaBadRequest(BaseModel):
    text: str = Field(title="エラーメッセージ")
    error_name: str = Field(
        title="エラー名",
        description="|name|description|\n|---|---|\n"
        + "\n".join(
            [
                "| {} | {} |".format(err.name, err.value)
                for err in list(ParseKanaErrorCode)
            ]
        ),
    )
    error_args: dict[str, str] = Field(title="エラーを起こした箇所")

    def __init__(self, err: ParseKanaError):
        super().__init__(text=err.text, error_name=err.errname, error_args=err.kwargs)


class MorphableTargetInfo(BaseModel):
    is_morphable: bool = Field(title="指定した話者に対してモーフィングの可否")
    # FIXME: add reason property
    # reason: str | None = Field(title="is_morphableがfalseである場合、その理由")


class StyleIdNotFoundError(LookupError):
    def __init__(self, style_id: int, *args: object, **kywrds: object) -> None:
        self.style_id = style_id
        super().__init__(f"style_id {style_id} is not found.", *args, **kywrds)


class LibrarySpeaker(BaseModel):
    """
    音声ライブラリに含まれる話者の情報
    """

    speaker: Speaker = Field(title="話者情報")
    speaker_info: SpeakerInfo = Field(title="話者の追加情報")


class BaseLibraryInfo(BaseModel):
    """
    音声ライブラリの情報
    """

    name: str = Field(title="音声ライブラリの名前")
    uuid: str = Field(title="音声ライブラリのUUID")
    version: str = Field(title="音声ライブラリのバージョン")
    download_url: str = Field(title="音声ライブラリのダウンロードURL")
    bytes: int = Field(title="音声ライブラリのバイト数")
    speakers: list[LibrarySpeaker] = Field(title="音声ライブラリに含まれる話者のリスト")


# 今後InstalledLibraryInfo同様に拡張する可能性を考え、モデルを分けている
class DownloadableLibraryInfo(BaseLibraryInfo):
    """
    ダウンロード可能な音声ライブラリの情報
    """

    pass


class InstalledLibraryInfo(BaseLibraryInfo):
    """
    インストール済み音声ライブラリの情報
    """

    uninstallable: bool = Field(title="アンインストール可能かどうか")


class SupportedFeaturesInfo(BaseModel):
    """
    エンジンの機能の情報
    """

    support_adjusting_mora: bool = Field(title="モーラが調整可能かどうか")
    support_adjusting_speed_scale: bool = Field(title="話速が調整可能かどうか")
    support_adjusting_pitch_scale: bool = Field(title="音高が調整可能かどうか")
    support_adjusting_intonation_scale: bool = Field(title="抑揚が調整可能かどうか")
    support_adjusting_volume_scale: bool = Field(title="音量が調整可能かどうか")
    support_adjusting_silence_scale: bool = Field(
        title="前後の無音時間が調節可能かどうか"
    )
    support_interrogative_upspeak: bool = Field(
        title="疑似疑問文に対応しているかどうか"
    )
    support_switching_device: bool = Field(title="CPU/GPUの切り替えが可能かどうか")


class VvlibManifest(BaseModel):
    """
    vvlib(VOICEVOX Library)に関する情報
    """

    manifest_version: StrictStr = Field(title="マニフェストバージョン")
    name: StrictStr = Field(title="音声ライブラリ名")
    version: StrictStr = Field(title="音声ライブラリバージョン")
    uuid: StrictStr = Field(title="音声ライブラリのUUID")
    brand_name: StrictStr = Field(title="エンジンのブランド名")
    engine_name: StrictStr = Field(title="エンジン名")
    engine_uuid: StrictStr = Field(title="エンジンのUUID")
