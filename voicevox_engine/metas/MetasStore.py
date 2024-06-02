import json
from copy import deepcopy
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from voicevox_engine.core.core_adapter import CoreSpeaker, CoreSpeakerStyle
from voicevox_engine.metas.Metas import (
    Speaker,
    SpeakerStyle,
    SpeakerSupportedFeatures,
    StyleId,
    StyleType,
)


def cast_styles(cores: list[CoreSpeakerStyle]) -> list[SpeakerStyle]:
    """コアから取得したスタイル情報をエンジン形式へキャストする。"""
    return [
        SpeakerStyle(name=core.name, id=StyleId(core.id), type=core.type)
        for core in cores
    ]


class _EngineSpeaker(BaseModel):
    """
    エンジンに含まれる話者情報
    """

    supported_features: SpeakerSupportedFeatures = Field(
        default_factory=SpeakerSupportedFeatures
    )


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
        self._loaded_metas: dict[str, _EngineSpeaker] = {
            folder.name: _EngineSpeaker(
                **json.loads((folder / "metas.json").read_text(encoding="utf-8"))
            )
            for folder in engine_speakers_path.iterdir()
        }

    def load_combined_metas(self, core_metas: list[CoreSpeaker]) -> list[Speaker]:
        """コアとエンジンのメタ情報を統合する。"""
        return [
            Speaker(
                supported_features=self._loaded_metas[
                    speaker_meta.speaker_uuid
                ].supported_features,
                name=speaker_meta.name,
                speaker_uuid=speaker_meta.speaker_uuid,
                styles=cast_styles(speaker_meta.styles),
                version=speaker_meta.version,
            )
            for speaker_meta in core_metas
        ]


def construct_lookup(
    speakers: list[Speaker],
) -> dict[StyleId, tuple[Speaker, SpeakerStyle]]:
    """
    スタイルID に話者メタ情報・スタイルメタ情報を紐付ける対応表を生成
    Parameters
    ----------
    speakers : list[Speaker]
        話者メタ情報
    Returns
    -------
    ret : dict[StyleId, tuple[Speaker, SpeakerStyle]]
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
