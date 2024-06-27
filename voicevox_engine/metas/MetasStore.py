"""キャラクター情報とキャラクターメタ情報の管理"""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Final, Literal, TypeAlias

from fastapi import HTTPException
from pydantic import BaseModel, Field

from voicevox_engine.core.core_adapter import CoreCharacter, CoreCharacterStyle
from voicevox_engine.metas.Metas import (
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


_TALK_STYLE_TYPES: Final = ["talk"]
_SING_STYLE_TYPES: Final = ["singing_teacher", "frame_decode", "sing"]


class _EngineCharacter(BaseModel):
    """
    エンジンに含まれるキャラクター情報
    """

    supported_features: SpeakerSupportedFeatures = Field(
        default_factory=SpeakerSupportedFeatures
    )


GetCoreCharacters: TypeAlias = Callable[[str | None], list[CoreCharacter]]


class MetasStore:
    """キャラクターやスタイルのメタ情報を管理する"""

    def __init__(
        self,
        engine_characters_path: Path,
        get_core_characters: GetCoreCharacters,
        resource_manager: ResourceManager,
    ) -> None:
        """
        インスタンスを生成する。

        Parameters
        ----------
        engine_characters_path : Path
            エンジンに含まれるキャラクターメタ情報ディレクトリのパス。
        get_core_characters:
            コアに含まれるキャラクター情報を返す関数
        """
        self._characters_path = engine_characters_path
        self._get_core_characters = get_core_characters
        self._resource_manager = resource_manager
        # エンジンに含まれる各キャラクターのメタ情報
        self._loaded_metas: dict[str, _EngineCharacter] = {
            folder.name: _EngineCharacter.model_validate_json(
                (folder / "metas.json").read_text(encoding="utf-8")
            )
            for folder in engine_characters_path.iterdir()
            if folder.is_dir()
        }

    def characters(self, core_version: str | None) -> list[Character]:
        """キャラクターの情報の一覧を取得する。"""

        # エンジンとコアのキャラクター情報を統合する
        characters: list[Character] = []
        for core_character in self._get_core_characters(core_version):
            character_uuid = core_character.speaker_uuid
            engine_character = self._loaded_metas[character_uuid]
            styles = cast_styles(core_character.styles)
            talk_styles = list(
                filter(lambda style: style.type in _TALK_STYLE_TYPES, styles)
            )
            sing_styles = list(
                filter(lambda style: style.type in _SING_STYLE_TYPES, styles)
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

    def character_info(
        self,
        character_uuid: str,
        talk_or_sing: Literal["talk", "sing"],
        core_version: str | None,
        resource_baseurl: str,
        resource_format: ResourceFormat,
    ) -> SpeakerInfo:
        # キャラクター情報は以下のディレクトリ構造に従わなければならない。
        # {engine_characters_path}/
        #     {character_uuid_0}/
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
        #     {character_uuid_1}/
        #         ...

        # 該当キャラクターを検索する
        characters = self.characters(core_version)
        characters = filter_characters_and_styles(characters, talk_or_sing)
        character = next(
            filter(lambda character: character.uuid == character_uuid, characters), None
        )
        if character is None:
            # FIXME: HTTPExceptionはこのファイルとドメインが合わないので辞める
            msg = "該当するキャラクターが見つかりません"
            raise HTTPException(status_code=404, detail=msg)

        # キャラクター情報を取得する
        try:
            character_path = self._characters_path / character_uuid

            # character policy
            policy_path = character_path / "policy.md"
            policy = policy_path.read_text("utf-8")

            def _resource_str(path: Path) -> str:
                resource_str = self._resource_manager.resource_str(
                    path, "hash" if resource_format == "url" else "base64"
                )
                if resource_format == "base64":
                    return resource_str
                return f"{resource_baseurl}/{resource_str}"

            # character portrait
            portrait_path = character_path / "portrait.png"
            portrait = _resource_str(portrait_path)

            # スタイル情報を取得する
            style_infos = []
            for style in character.talk_styles + character.sing_styles:
                id = style.id

                # style icon
                style_icon_path = character_path / "icons" / f"{id}.png"
                icon = _resource_str(style_icon_path)

                # style portrait
                style_portrait_path = character_path / "portraits" / f"{id}.png"
                style_portrait = None
                if style_portrait_path.exists():
                    style_portrait = _resource_str(style_portrait_path)

                # voice samples
                voice_samples: list[str] = []
                for j in range(3):
                    num = str(j + 1).zfill(3)
                    voice_path = character_path / "voice_samples" / f"{id}_{num}.wav"
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

        character_info = SpeakerInfo(
            policy=policy, portrait=portrait, style_infos=style_infos
        )
        return character_info

    def talk_characters(self, core_version: str | None) -> list[Character]:
        """話せるキャラクターの情報の一覧を取得する。"""
        return filter_characters_and_styles(self.characters(core_version), "talk")

    def sing_characters(self, core_version: str | None) -> list[Character]:
        """歌えるキャラクターの情報の一覧を取得する。"""
        return filter_characters_and_styles(self.characters(core_version), "sing")


def filter_characters_and_styles(
    characters: list[Character],
    talk_or_sing: Literal["talk", "sing"],
) -> list[Character]:
    """キャラクター内のスタイルをtalk系・sing系のみにする。スタイル数が0になったキャラクターは除外する。"""
    if talk_or_sing == "talk":
        # talk 系スタイルを持たないキャラクターを除外する
        talk_characters = list(
            filter(lambda character: len(character.talk_styles) > 0, characters)
        )
        # sing 系スタイルを除外する
        for talk_character in talk_characters:
            talk_character.sing_styles = []
        return talk_characters
    elif talk_or_sing == "sing":
        # sing 系スタイルを持たないキャラクターを除外する
        sing_characters = list(
            filter(lambda character: len(character.sing_styles) > 0, characters)
        )
        # talk 系スタイルを除外する
        for sing_character in sing_characters:
            sing_character.talk_styles = []
        return sing_characters
    else:
        raise Exception(f"'{talk_or_sing}' は不正な style_type です")
