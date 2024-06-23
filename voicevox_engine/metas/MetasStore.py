"""話者情報と話者メタ情報の管理"""

import base64
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, TypeAlias

from fastapi import HTTPException
from pydantic import BaseModel, Field

from voicevox_engine.core.core_adapter import CoreCharacter, CoreCharacterStyle
from voicevox_engine.metas.Metas import (
    Speaker,
    SpeakerInfo,
    SpeakerStyle,
    SpeakerSupportedFeatures,
    StyleId,
)
from voicevox_engine.resource_manager import ResourceManager, ResourceManagerError

ResourceFormat: TypeAlias = Literal["base64", "url"]


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

    def __init__(
        self, engine_speakers_path: Path, resource_manager: ResourceManager
    ) -> None:
        """
        Parameters
        ----------
        engine_speakers_path : Path
            エンジンに含まれる話者メタ情報ディレクトリのパス。
        """
        self._speakers_path = engine_speakers_path
        self._resource_manager = resource_manager
        # エンジンに含まれる各話者のメタ情報
        self._loaded_metas: dict[str, _EngineSpeaker] = {
            folder.name: _EngineSpeaker.model_validate_json(
                (folder / "metas.json").read_text(encoding="utf-8")
            )
            for folder in engine_speakers_path.iterdir()
            if folder.is_dir()
        }

    def load_combined_metas(
        self, core_characters: list[CoreCharacter]
    ) -> list[Character]:
        """コアとエンジンのメタ情報を統合する。"""
        characters: list[Character] = []
        for core_character in core_characters:
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

    def speaker_info(
        self,
        speaker_uuid: str,
        speaker_or_singer: Literal["speaker", "singer"],
        core_characters: list[CoreCharacter],
        resource_baseurl: str,
        resource_format: ResourceFormat,
    ) -> SpeakerInfo:
        # キャラクター情報は以下のディレクトリ構造に従わなければならない。
        # {engine_speakers_path}/
        #     {speaker_uuid_0}/
        #         policy.md
        #         portrait.png
        #         icons/
        #             {id_0}.png
        #             {id_1}.png
        #             ...
        #         portraits/
        #             {id_0}.png
        #             {id_1}.png
        #             ...
        #         voice_samples/
        #             {id_0}_001.wav
        #             {id_0}_002.wav
        #             {id_0}_003.wav
        #             {id_1}_001.wav
        #             ...
        #     {speaker_uuid_1}/
        #         ...

        # 該当話者を検索する
        characters = self.load_combined_metas(core_characters)
        speakers = filter_characters_and_styles(characters, speaker_or_singer)
        speaker = next(
            filter(lambda spk: spk.speaker_uuid == speaker_uuid, speakers), None
        )
        if speaker is None:
            # FIXME: HTTPExceptionはこのファイルとドメインが合わないので辞める
            raise HTTPException(status_code=404, detail="該当する話者が見つかりません")

        # 話者情報を取得する
        try:
            speaker_path = self._speakers_path / speaker_uuid

            # speaker policy
            policy_path = speaker_path / "policy.md"
            policy = policy_path.read_text("utf-8")

            def _resource_str(path: Path) -> str:
                resource_str = self._resource_manager.resource_str(
                    path, "hash" if resource_format == "url" else "base64"
                )
                if resource_format == "base64":
                    return resource_str
                return f"{resource_baseurl}/{resource_str}"

            # speaker portrait
            portrait_path = speaker_path / "portrait.png"
            portrait = _resource_str(portrait_path)

            # スタイル情報を取得する
            style_infos = []
            for style in speaker.styles:
                id = style.id

                # style icon
                style_icon_path = speaker_path / "icons" / f"{id}.png"
                icon = _resource_str(style_icon_path)

                # style portrait
                style_portrait_path = speaker_path / "portraits" / f"{id}.png"
                style_portrait = None
                if style_portrait_path.exists():
                    style_portrait = _resource_str(style_portrait_path)

                # voice samples
                voice_samples: list[str] = []
                for j in range(3):
                    num = str(j + 1).zfill(3)
                    voice_path = speaker_path / "voice_samples" / f"{id}_{num}.wav"
                    voice_samples.append(_resource_str(voice_path))

                style_infos.append(
                    {
                        "id": id,
                        "icon": icon,
                        "portrait": style_portrait,
                        "voice_samples": voice_samples,
                    }
                )
        except (FileNotFoundError, ResourceManagerError):
            # FIXME: HTTPExceptionはこのファイルとドメインが合わないので辞める
            msg = "追加情報が見つかりませんでした"
            raise HTTPException(status_code=500, detail=msg)

        spk_info = SpeakerInfo(
            policy=policy, portrait=portrait, style_infos=style_infos
        )
        return spk_info

    def talk_characters(self, core_characters: list[CoreCharacter]) -> list[Speaker]:
        """話せるキャラクターの情報の一覧を取得する。"""
        characters = self.load_combined_metas(core_characters)
        return filter_characters_and_styles(characters, "speaker")

    def sing_characters(self, core_characters: list[CoreCharacter]) -> list[Speaker]:
        """歌えるキャラクターの情報の一覧を取得する。"""
        characters = self.load_combined_metas(core_characters)
        return filter_characters_and_styles(characters, "singer")


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
