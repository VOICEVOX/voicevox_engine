from pydantic import BaseModel, Field

from voicevox_engine.tts_pipeline.model import AccentPhrase


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


class MorphableTargetInfo(BaseModel):
    is_morphable: bool = Field(title="指定した話者に対してモーフィングの可否")
    # FIXME: add reason property
    # reason: str | None = Field(title="is_morphableがfalseである場合、その理由")


class StyleIdNotFoundError(LookupError):
    def __init__(self, style_id: int, *args: object, **kywrds: object) -> None:
        self.style_id = style_id
        super().__init__(f"style_id {style_id} is not found.", *args, **kywrds)


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
