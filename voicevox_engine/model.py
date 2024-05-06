"""
API と ENGINE 内部実装が共有するモデル

このモジュールで定義されるモデル（データ構造）は API と ENGINE の 2 箇所から使われる。そのため
- モデルの変更は API 変更となるため慎重に検討する。
- モデルの docstring や Field は API スキーマとして使われるため、ユーザー向けに丁寧に書く。
- モデルクラスは FastAPI の制約から `BaseModel` を継承しなければならない。
"""

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
        default=None,
        title="[読み取り専用]AquesTalk 風記法によるテキスト。音声合成用のクエリとしては無視される",
    )

    def __hash__(self) -> int:
        items = [
            (k, tuple(v)) if isinstance(v, list) else (k, v)
            for k, v in self.__dict__.items()
        ]
        return hash(tuple(sorted(items)))
