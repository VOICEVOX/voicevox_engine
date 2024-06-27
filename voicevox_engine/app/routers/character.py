"""キャラクター情報機能を提供する API Router"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic.json_schema import SkipJsonSchema

from voicevox_engine.metas.Metas import Speaker, SpeakerInfo
from voicevox_engine.metas.MetasStore import Character, MetasStore, ResourceFormat
from voicevox_engine.resource_manager import ResourceManager, ResourceManagerError

RESOURCE_ENDPOINT = "_resources"


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
    resource_manager: ResourceManager, metas_store: MetasStore
) -> APIRouter:
    """キャラクター情報 API Router を生成する"""
    router = APIRouter(tags=["その他"])

    @router.get("/speakers")
    def speakers(core_version: str | SkipJsonSchema[None] = None) -> list[Speaker]:
        """喋れるキャラクターの情報の一覧を返します。"""
        characters = metas_store.talk_characters(core_version)
        return _characters_to_speakers(characters)

    @router.get("/speaker_info")
    def speaker_info(
        resource_baseurl: Annotated[str, Depends(_get_resource_baseurl)],
        speaker_uuid: str,
        resource_format: ResourceFormat = "base64",
        core_version: str | SkipJsonSchema[None] = None,
    ) -> SpeakerInfo:
        """
        UUID で指定された喋れるキャラクターの情報を返します。
        画像や音声はresource_formatで指定した形式で返されます。
        """
        return metas_store.character_info(
            character_uuid=speaker_uuid,
            talk_or_sing="talk",
            core_version=core_version,
            resource_baseurl=resource_baseurl,
            resource_format=resource_format,
        )

    @router.get("/singers")
    def singers(core_version: str | SkipJsonSchema[None] = None) -> list[Speaker]:
        """歌えるキャラクターの情報の一覧を返します。"""
        characters = metas_store.sing_characters(core_version)
        return _characters_to_speakers(characters)

    @router.get("/singer_info")
    def singer_info(
        resource_baseurl: Annotated[str, Depends(_get_resource_baseurl)],
        speaker_uuid: str,
        resource_format: ResourceFormat = "base64",
        core_version: str | SkipJsonSchema[None] = None,
    ) -> SpeakerInfo:
        """
        UUID で指定された歌えるキャラクターの情報を返します。
        画像や音声はresource_formatで指定した形式で返されます。
        """
        return metas_store.character_info(
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
