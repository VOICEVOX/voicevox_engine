"""話者情報機能を提供する API Router"""

from pathlib import Path
from typing import Annotated, Literal, TypeAlias

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic.json_schema import SkipJsonSchema

from voicevox_engine.core.core_initializer import CoreManager
from voicevox_engine.metas.Metas import Speaker, SpeakerInfo
from voicevox_engine.metas.MetasStore import (
    Character,
    MetasStore,
    filter_characters_and_styles,
)
from voicevox_engine.resource_manager import ResourceManager, ResourceManagerError

RESOURCE_ENDPOINT = "_resources"
ResourceFormat: TypeAlias = Literal["base64", "url"]


async def _get_resource_baseurl(request: Request) -> str:
    return f"{request.url.scheme}://{request.url.netloc}/{RESOURCE_ENDPOINT}"


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
    resource_manager: ResourceManager,
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
        resource_baseurl: Annotated[str, Depends(_get_resource_baseurl)],
        speaker_uuid: str,
        resource_format: ResourceFormat = "base64",
        core_version: str | SkipJsonSchema[None] = None,
    ) -> SpeakerInfo:
        """
        指定されたspeaker_uuidの話者に関する情報をjson形式で返します。
        画像や音声はresource_formatで指定した形式で返されます。
        """
        return _character_info(
            character_uuid=speaker_uuid,
            talk_or_sing="talk",
            core_version=core_version,
            resource_baseurl=resource_baseurl,
            resource_format=resource_format,
        )

    # FIXME: この関数をどこかに切り出す
    def _character_info(
        character_uuid: str,
        talk_or_sing: Literal["talk", "sing"],
        core_version: str | None,
        resource_baseurl: str,
        resource_format: ResourceFormat,
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

            def _resource_str(path: Path) -> str:
                resource_str = resource_manager.resource_str(
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
        resource_baseurl: Annotated[str, Depends(_get_resource_baseurl)],
        speaker_uuid: str,
        resource_format: ResourceFormat = "base64",
        core_version: str | SkipJsonSchema[None] = None,
    ) -> SpeakerInfo:
        """
        指定されたspeaker_uuidの歌手に関する情報をjson形式で返します。
        画像や音声はresource_formatで指定した形式で返されます。
        """
        return _character_info(
            character_uuid=speaker_uuid,
            talk_or_sing="sing",
            core_version=core_version,
            resource_baseurl=resource_baseurl,
            resource_format=resource_format,
        )

    # リソースはAPIとしてアクセスするものではないことを表明するためOpenAPIスキーマーから除外する
    @router.get(f"/{RESOURCE_ENDPOINT}/{{resource_hash}}", include_in_schema=False)
    async def resources(resource_hash: str) -> FileResponse:
        """
        ResourceManagerから発行されたハッシュ値に対応するリソースファイルを返す
        """
        try:
            resource_path = resource_manager.resource_path(resource_hash)
        except ResourceManagerError:
            raise HTTPException(status_code=404)
        return FileResponse(
            resource_path,
            headers={"Cache-Control": "max-age=2592000"},  # 30日
        )

    return router
