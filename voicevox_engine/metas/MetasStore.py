import json
from copy import deepcopy
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Literal, Tuple

from pydantic import BaseModel, Field

from voicevox_engine.metas.Metas import (
    EngineSpeaker,
    Speaker,
    SpeakerStyle,
    StyleId,
    StyleType,
)

if TYPE_CHECKING:
    from voicevox_engine.core.core_adapter import CoreAdapter


class CoreSpeaker(BaseModel):
    """
    コアに含まれる話者情報
    """

    name: str = Field(title="名前")
    speaker_uuid: str = Field(title="話者のUUID")
    styles: List[SpeakerStyle] = Field(title="スタイルの一覧")
    version: str = Field("話者のバージョン")


class MetasStore:
    """
    話者やスタイルのメタ情報を管理する
    """

    def __init__(self, engine_speakers_path: Path) -> None:
        """
        Parameters
        ----------
        engine_speakers_path : Path
            エンジンに含まれる話者メタ情報ディレクトリのパス。
        """
        # エンジンに含まれる各話者のメタ情報
        self._loaded_metas: Dict[str, EngineSpeaker] = {
            folder.name: EngineSpeaker(
                **json.loads((folder / "metas.json").read_text(encoding="utf-8"))
            )
            for folder in engine_speakers_path.iterdir()
        }

    # FIXME: engineではなくList[CoreSpeaker]を渡す形にすることで
    # TTSEngineによる循環importを修正する
    def load_combined_metas(self, core: "CoreAdapter") -> List[Speaker]:
        """
        コアに含まれる話者メタ情報とエンジンに含まれる話者メタ情報を統合
        Parameters
        ----------
        core : CoreAdapter
            話者メタ情報をもったコア
        Returns
        -------
        ret : List[Speaker]
            エンジンとコアに含まれる話者メタ情報
        """
        # コアに含まれる話者メタ情報の収集
        core_metas = [CoreSpeaker(**speaker) for speaker in json.loads(core.speakers)]
        # エンジンに含まれる話者メタ情報との統合
        return [
            Speaker(
                **self._loaded_metas[speaker_meta.speaker_uuid].dict(),
                name=speaker_meta.name,
                speaker_uuid=speaker_meta.speaker_uuid,
                styles=speaker_meta.styles,
                version=speaker_meta.version,
            )
            for speaker_meta in core_metas
        ]


def construct_lookup(
    speakers: List[Speaker],
) -> Dict[StyleId, Tuple[Speaker, SpeakerStyle]]:
    """
    スタイルID に話者メタ情報・スタイルメタ情報を紐付ける対応表を生成
    Parameters
    ----------
    speakers : List[Speaker]
        話者メタ情報
    Returns
    -------
    ret : Dict[StyleId, Tuple[Speaker, SpeakerStyle]]
        スタイルID に話者メタ情報・スタイルメタ情報が紐付いた対応表
    """
    lookup_table: dict[StyleId, tuple[Speaker, SpeakerStyle]] = dict()
    for speaker in speakers:
        for style in speaker.styles:
            lookup_table[style.id] = (speaker, style)
    return lookup_table


def filter_speakers_and_styles(
    speakers: list[Speaker],
    speaker_or_singer: Literal["speaker", "singer"],
) -> list[Speaker]:
    """
    話者・スタイルをフィルタリングする。
    speakerの場合はトーク系スタイルのみ、singerの場合はソング系スタイルのみを残す。
    スタイル数が0になった話者は除外する。
    """
    style_types: list[StyleType]
    if speaker_or_singer == "speaker":
        style_types = ["talk"]
    elif speaker_or_singer == "singer":
        style_types = ["singing_teacher", "frame_decode", "sing"]

    speakers = deepcopy(speakers)
    for speaker in speakers:
        speaker.styles = [
            style for style in speaker.styles if style.type in style_types
        ]
    return [speaker for speaker in speakers if len(speaker.styles) > 0]
