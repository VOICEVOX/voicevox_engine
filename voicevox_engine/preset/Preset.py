from pydantic import BaseModel, Field

from voicevox_engine.metas.Metas import StyleId


class Preset(BaseModel):
    """
    プリセット情報
    """

    id: int = Field(title="プリセットID")
    name: str = Field(title="プリセット名")
    speaker_uuid: str = Field(title="話者のUUID")
    style_id: StyleId = Field(title="スタイルID")
    speedScale: float = Field(title="全体の話速")
    pitchScale: float = Field(title="全体の音高")
    intonationScale: float = Field(title="全体の抑揚")
    volumeScale: float = Field(title="全体の音量")
    prePhonemeLength: float = Field(title="音声の前の無音時間")
    postPhonemeLength: float = Field(title="音声の後の無音時間")
    pauseLength: float = Field(title="テキスト内の無音時間")
    isPauseLengthFixed: bool = Field(title="無音時間(絶対値)が話速の影響を受けるか")
    pauseLengthScale: float = Field(title="テキスト内の無音時間(倍率)")
