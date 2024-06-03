"""話者情報と話者メタ情報の管理"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

from pydantic import BaseModel, Field

from voicevox_engine.core.core_adapter import CoreSpeaker, CoreSpeakerStyle
from voicevox_engine.metas.Metas import (
    Speaker,
    SpeakerStyle,
    SpeakerSupportedFeatures,
    StyleId,
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
            if folder.is_dir()
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


@dataclass
class Character:
    """キャラクター"""

    name: str
    uuid: str
    talk_styles: list[SpeakerStyle]
    sing_styles: list[SpeakerStyle]
    version: str
    supported_features: SpeakerSupportedFeatures


TALK_STYLE_TYPES: Final = ["talk"]
SING_STYLE_TYPES: Final = ["singing_teacher", "frame_decode", "sing"]


def filter_speakers_and_styles(
    speakers: list[Speaker],
    speaker_or_singer: Literal["speaker", "singer"],
) -> list[Speaker]:
    """キャラクター内のスタイルをtalk系・sing系のみにする。スタイル数が0になったキャラクターは除外する。"""

    characters = map(
        lambda speaker: Character(
            name=speaker.name,
            uuid=speaker.speaker_uuid,
            talk_styles=list(
                filter(lambda style: style.type in TALK_STYLE_TYPES, speaker.styles)
            ),
            sing_styles=list(
                filter(lambda style: style.type in SING_STYLE_TYPES, speaker.styles)
            ),
            version=speaker.version,
            supported_features=speaker.supported_features,
        ),
        speakers,
    )

    if speaker_or_singer == "speaker":
        # talk 系スタイルを持たないキャラクターを除外する
        talk_characters = filter(
            lambda character: len(character.talk_styles) > 0, characters
        )
        # キャラクター内のスタイルを talk 系のみにしたうえでキャストする
        talk_speakers = map(
            lambda talker: Speaker(
                name=talker.name,
                speaker_uuid=talker.uuid,
                styles=talker.talk_styles,
                version=talker.version,
                supported_features=talker.supported_features,
            ),
            talk_characters,
        )
        return list(talk_speakers)
    elif speaker_or_singer == "singer":
        # sing 系スタイルを持たないキャラクターを除外する
        sing_characters = filter(
            lambda character: len(character.sing_styles) > 0, characters
        )
        # キャラクター内のスタイルを sing 系のみにしたうえでキャストする
        sing_speakers = map(
            lambda singer: Speaker(
                name=singer.name,
                speaker_uuid=singer.uuid,
                styles=singer.sing_styles,
                version=singer.version,
                supported_features=singer.supported_features,
            ),
            sing_characters,
        )
        return list(sing_speakers)
    else:
        raise Exception(f"'{speaker_or_singer}' は不正な style_type です")
