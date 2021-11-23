from pydantic import BaseModel, Field


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
