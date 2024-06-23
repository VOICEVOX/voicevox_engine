"""話者情報機能を提供する API Router"""

import base64
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic.json_schema import SkipJsonSchema

from voicevox_engine.core.core_initializer import CoreManager
from voicevox_engine.metas.Metas import Speaker, SpeakerInfo
from voicevox_engine.metas.MetasStore import (
    Character,
    MetasStore,
    filter_characters_and_styles,
)


def b64encode_str(s: bytes) -> str:
    return base64.b64encode(s).decode("utf-8")


def _characters_to_speakers(characters: list[Character]) -> list[Speaker]:
    """キャラクターのリストを `Speaker` のリストへキャストする。"""
    return list(
        map(
            lambda character: Speaker(
                name=character.name,
                speaker_uuid=character.uuid,
                styles=character.talk_styles + character.sing_styles,
                version=character.version,
                supported_features=character.supported_features,
            ),
            characters,
        )
    )


def generate_character_router(
    core_manager: CoreManager,
    metas_store: MetasStore,
    character_info_dir: Path,
) -> APIRouter:
    """話者情報 API Router を生成する"""
    router = APIRouter(tags=["その他"])

    @router.get("/speakers")
    def speakers(core_version: str | SkipJsonSchema[None] = None) -> list[Speaker]:
        """話者情報の一覧を取得します。"""
        version = core_version or core_manager.latest_version()
        core = core_manager.get_core(version)
        characters = metas_store.talk_characters(core.characters)
        return _characters_to_speakers(characters)

    @router.get("/speaker_info")
    def speaker_info(
        speaker_uuid: str, core_version: str | SkipJsonSchema[None] = None
    ) -> SpeakerInfo:
        """
        指定されたspeaker_uuidの話者に関する情報をjson形式で返します。
        画像や音声はbase64エンコードされたものが返されます。
        """
        return _character_info(
            character_uuid=speaker_uuid, talk_or_sing="talk", core_version=core_version
        )

    # FIXME: この関数をどこかに切り出す
    def _character_info(
        character_uuid: str,
        talk_or_sing: Literal["talk", "sing"],
        core_version: str | None,
    ) -> SpeakerInfo:
        # エンジンに含まれる話者メタ情報は、次のディレクトリ構造に従わなければならない：
        # {root_dir}/
        #   character_info/
        #       {speaker_uuid_0}/
        #           policy.md
        #           portrait.png
        #           icons/
        #               {id_0}.png
        #               {id_1}.png
        #               ...
        #           portraits/
        #               {id_0}.png
        #               {id_1}.png
        #               ...
        #           voice_samples/
        #               {id_0}_001.wav
        #               {id_0}_002.wav
        #               {id_0}_003.wav
        #               {id_1}_001.wav
        #               ...
        #       {speaker_uuid_1}/
        #           ...

        version = core_version or core_manager.latest_version()

        # 該当話者を検索する
        core_characters = core_manager.get_core(version).characters
        characters = metas_store.load_combined_metas(core_characters)
        characters = filter_characters_and_styles(characters, talk_or_sing)
        character = next(
            filter(lambda character: character.uuid == character_uuid, characters), None
        )
        if character is None:
            raise HTTPException(status_code=404, detail="該当する話者が見つかりません")

        # 話者情報を取得する
        try:
            character_path = character_info_dir / character_uuid

            # character policy
            policy_path = character_path / "policy.md"
            policy = policy_path.read_text("utf-8")

            # character portrait
            portrait_path = character_path / "portrait.png"
            portrait = b64encode_str(portrait_path.read_bytes())

            # スタイル情報を取得する
            style_infos = []
            for style in character.talk_styles + character.sing_styles:
                id = style.id

                # style icon
                style_icon_path = character_path / "icons" / f"{id}.png"
                icon = b64encode_str(style_icon_path.read_bytes())

                # style portrait
                style_portrait_path = character_path / "portraits" / f"{id}.png"
                style_portrait = None
                if style_portrait_path.exists():
                    style_portrait = b64encode_str(style_portrait_path.read_bytes())

                # voice samples
                voice_samples: list[str] = []
                for j in range(3):
                    num = str(j + 1).zfill(3)
                    voice_path = character_path / "voice_samples" / f"{id}_{num}.wav"
                    voice_samples.append(b64encode_str(voice_path.read_bytes()))

                style_infos.append(
                    {
                        "id": id,
                        "icon": icon,
                        "portrait": style_portrait,
                        "voice_samples": voice_samples,
                    }
                )
        except FileNotFoundError:
            msg = "追加情報が見つかりませんでした"
            raise HTTPException(status_code=500, detail=msg)

        character_info = SpeakerInfo(
            policy=policy, portrait=portrait, style_infos=style_infos
        )
        return character_info

    @router.get("/singers")
    def singers(core_version: str | SkipJsonSchema[None] = None) -> list[Speaker]:
        """歌手情報の一覧を取得します"""
        version = core_version or core_manager.latest_version()
        core = core_manager.get_core(version)
        characters = metas_store.sing_characters(core.characters)
        return _characters_to_speakers(characters)

    @router.get("/singer_info")
    def singer_info(
        speaker_uuid: str, core_version: str | SkipJsonSchema[None] = None
    ) -> SpeakerInfo:
        """
        指定されたspeaker_uuidの歌手に関する情報をjson形式で返します。
        画像や音声はbase64エンコードされたものが返されます。
        """
        return _character_info(
            character_uuid=speaker_uuid, talk_or_sing="sing", core_version=core_version
        )

    return router
