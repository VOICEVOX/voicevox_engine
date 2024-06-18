"""話者情報機能を提供する API Router"""

from pathlib import Path
from typing import Annotated, Literal, TypeAlias

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import TypeAdapter
from pydantic.json_schema import SkipJsonSchema

from voicevox_engine.core.core_initializer import CoreManager
from voicevox_engine.metas.Metas import Speaker, SpeakerInfo
from voicevox_engine.metas.MetasStore import MetasStore, filter_speakers_and_styles
from voicevox_engine.resource_manager import ResourceManager, ResourceManagerError

RESOURCE_ENDPOINT = "_resources"
ResourceFormat: TypeAlias = Literal["base64", "url"]


async def get_resource_baseurl(request: Request) -> str:
    return f"{request.url.scheme}://{request.url.netloc}/{RESOURCE_ENDPOINT}"


def generate_speaker_router(
    core_manager: CoreManager,
    resource_manager: ResourceManager,
    metas_store: MetasStore,
    speaker_info_dir: Path,
) -> APIRouter:
    """話者情報 API Router を生成する"""
    router = APIRouter(tags=["その他"])

    @router.get("/speakers")
    def speakers(core_version: str | SkipJsonSchema[None] = None) -> list[Speaker]:
        """話者情報の一覧を取得します。"""
        core = core_manager.get_core(core_version)
        speakers = metas_store.load_combined_metas(core.speakers)
        return filter_speakers_and_styles(speakers, "speaker")

    @router.get("/speaker_info")
    def speaker_info(
        resource_baseurl: Annotated[str, Depends(get_resource_baseurl)],
        speaker_uuid: str,
        resource_format: ResourceFormat = "base64",
        core_version: str | SkipJsonSchema[None] = None,
    ) -> SpeakerInfo:
        """
        指定されたspeaker_uuidの話者に関する情報をjson形式で返します。
        画像や音声はresource_formatで指定した形式で返されます。
        """
        return _speaker_info(
            speaker_uuid=speaker_uuid,
            speaker_or_singer="speaker",
            core_version=core_version,
            resource_baseurl=resource_baseurl,
            resource_format=resource_format,
        )

    _speaker_list_adapter = TypeAdapter(list[Speaker])

    # FIXME: この関数をどこかに切り出す
    def _speaker_info(
        speaker_uuid: str,
        speaker_or_singer: Literal["speaker", "singer"],
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

        # 該当話者を検索する
        speakers = _speaker_list_adapter.validate_python(
            core_manager.get_core(core_version).speakers, from_attributes=True
        )
        speakers = filter_speakers_and_styles(speakers, speaker_or_singer)
        speaker = next(
            filter(lambda spk: spk.speaker_uuid == speaker_uuid, speakers), None
        )
        if speaker is None:
            raise HTTPException(status_code=404, detail="該当する話者が見つかりません")

        # 話者情報を取得する
        try:
            speaker_path = speaker_info_dir / speaker_uuid

            # speaker policy
            policy_path = speaker_path / "policy.md"
            policy = policy_path.read_text("utf-8")

            def _resource_str(path: Path) -> str:
                return resource_manager.resource_str(
                    path, resource_baseurl, resource_format
                )

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
            msg = "追加情報が見つかりませんでした"
            raise HTTPException(status_code=500, detail=msg)

        spk_info = SpeakerInfo(
            policy=policy, portrait=portrait, style_infos=style_infos
        )
        return spk_info

    @router.get("/singers")
    def singers(core_version: str | SkipJsonSchema[None] = None) -> list[Speaker]:
        """歌手情報の一覧を取得します"""
        core = core_manager.get_core(core_version)
        singers = metas_store.load_combined_metas(core.speakers)
        return filter_speakers_and_styles(singers, "singer")

    @router.get("/singer_info")
    def singer_info(
        resource_baseurl: Annotated[str, Depends(get_resource_baseurl)],
        speaker_uuid: str,
        resource_format: ResourceFormat = "base64",
        core_version: str | SkipJsonSchema[None] = None,
    ) -> SpeakerInfo:
        """
        指定されたspeaker_uuidの歌手に関する情報をjson形式で返します。
        画像や音声はresource_formatで指定した形式で返されます。
        """
        return _speaker_info(
            speaker_uuid=speaker_uuid,
            speaker_or_singer="singer",
            core_version=core_version,
            resource_baseurl=resource_baseurl,
            resource_format=resource_format,
        )

    # リソースはAPIとしてアクセスするものではないことを表明するためOpenAPIスキーマーから除外する
    @router.get(f"/{RESOURCE_ENDPOINT}/{{resource_name}}", include_in_schema=False)
    async def resources(resource_hash: str) -> FileResponse:
        """
        ResourceManagerから発行されたハッシュ値に対応するリソースファイルを返す
        """
        resource_path = resource_manager.resource_path(resource_name)
        if resource_path is None or not resource_path.exists():
            raise HTTPException(status_code=404)
        return FileResponse(
            resource_path,
            headers={"Cache-Control": "max-age=2592000"}, # 30日
        )

    return router
