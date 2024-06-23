"""話者情報と話者メタ情報の管理"""

from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

from pydantic import BaseModel, Field

from voicevox_engine.core.core_adapter import CoreCharacterStyle
from voicevox_engine.core.core_initializer import CoreManager
from voicevox_engine.metas.Metas import (
    Speaker,
    SpeakerStyle,
    SpeakerSupportedFeatures,
    StyleId,
)


def cast_styles(cores: list[CoreCharacterStyle]) -> list[SpeakerStyle]:
    """コアから取得したスタイル情報をエンジン形式へキャストする。"""
    return [
        SpeakerStyle(name=core.name, id=StyleId(core.id), type=core.type)
        for core in cores
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


def characters_to_speakers(characters: list[Character]) -> list[Speaker]:
    """キャラクター配列を Speaker 配列へキャストする。"""
    return [
        Speaker(
            name=character.name,
            speaker_uuid=character.uuid,
            styles=character.talk_styles + character.sing_styles,
            version=character.version,
            supported_features=character.supported_features,
        )
        for character in characters
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

    def __init__(self, engine_speakers_path: Path, core_manager: CoreManager) -> None:
        """
        Parameters
        ----------
        engine_speakers_path : Path
            エンジンに含まれる話者メタ情報ディレクトリのパス。
        core_manager:
            コアマネージャー
        """
        self._core_manager = core_manager
        # エンジンに含まれる各話者のメタ情報
        self._loaded_metas: dict[str, _EngineSpeaker] = {
            folder.name: _EngineSpeaker.model_validate_json(
                (folder / "metas.json").read_text(encoding="utf-8")
            )
            for folder in engine_speakers_path.iterdir()
            if folder.is_dir()
        }

    def characters(self, core_version: str | None) -> list[Character]:
        """キャラクターの情報の一覧を取得する。"""
        version = core_version or self._core_manager.latest_version()
        core = self._core_manager.get_core(version)

        # エンジンとコアのキャラクター情報を統合する
        characters: list[Character] = []
        for core_character in core.characters:
            character_uuid = core_character.speaker_uuid
            engine_character = self._loaded_metas[character_uuid]
            styles = cast_styles(core_character.styles)
            talk_styles = list(
                filter(lambda style: style.type in TALK_STYLE_TYPES, styles)
            )
            sing_styles = list(
                filter(lambda style: style.type in SING_STYLE_TYPES, styles)
            )
            characters.append(
                Character(
                    name=core_character.name,
                    uuid=character_uuid,
                    talk_styles=talk_styles,
                    sing_styles=sing_styles,
                    version=core_character.version,
                    supported_features=engine_character.supported_features,
                )
            )
        return characters

    def talk_characters(self, core_version: str | None) -> list[Speaker]:
        """話せるキャラクターの情報の一覧を取得する。"""
        return filter_characters_and_styles(self.characters(core_version), "speaker")

    def sing_characters(self, core_version: str | None) -> list[Speaker]:
        """歌えるキャラクターの情報の一覧を取得する。"""
        return filter_characters_and_styles(self.characters(core_version), "singer")


def filter_characters_and_styles(
    characters: list[Character],
    speaker_or_singer: Literal["speaker", "singer"],
) -> list[Speaker]:
    """キャラクター内のスタイルをtalk系・sing系のみにする。スタイル数が0になったキャラクターは除外する。"""
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
