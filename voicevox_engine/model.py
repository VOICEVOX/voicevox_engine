"""
API と ENGINE 内部実装が共有するモデル

このモジュールで定義されるモデル（データ構造）は API と ENGINE の 2 箇所から使われる。そのため
- モデルの変更は API 変更となるため慎重に検討する。
- モデルの docstring や Field は API スキーマとして使われるため、ユーザー向けに丁寧に書く。
- モデルクラスは FastAPI の制約から `BaseModel` を継承しなければならない。
"""

from pydantic import BaseModel, Field
from pydantic.json_schema import SkipJsonSchema

from voicevox_engine.tts_pipeline.model import AccentPhrase


class AudioQuery(BaseModel):
    """
    音声合成用のクエリ
    """

    accent_phrases: list[AccentPhrase] = Field(description="アクセント句のリスト")
    speedScale: float = Field(description="全体の話速")
    pitchScale: float = Field(description="全体の音高")
    intonationScale: float = Field(description="全体の抑揚")
    volumeScale: float = Field(description="全体の音量")
    prePhonemeLength: float = Field(description="音声の前の無音時間")
    postPhonemeLength: float = Field(description="音声の後の無音時間")
    pauseLength: float | None = Field(
        default=None,
        description="句読点などの無音時間。nullのときは無視される。デフォルト値はnull",
    )
    pauseLengthScale: float = Field(
        default=1, description="句読点などの無音時間（倍率）。デフォルト値は1"
    )
    outputSamplingRate: int = Field(description="音声データの出力サンプリングレート")
    outputStereo: bool = Field(description="音声データをステレオ出力するか否か")
    kana: str | SkipJsonSchema[None] = Field(
        default=None,
        description="[読み取り専用]AquesTalk 風記法によるテキスト。音声合成用のクエリとしては無視される",
    )

    def __hash__(self) -> int:
        items = [
            (k, tuple(v)) if isinstance(v, list) else (k, v)
            for k, v in self.__dict__.items()
        ]
        return hash(tuple(sorted(items)))
