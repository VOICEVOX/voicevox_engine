"""話者情報機能を提供する API Router"""

import base64
import json
from os.path import basename
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse
from pydantic import parse_obj_as

from voicevox_engine.core.core_initializer import CoreManager
from voicevox_engine.metas.Metas import StyleId
from voicevox_engine.metas.MetasStore import MetasStore, filter_speakers_and_styles
from voicevox_engine.model import Speaker, SpeakerInfo


async def get_character_resource_baseurl(request: Request) -> str:
    return f"{request.url.scheme}://{request.url.netloc}/character_resources"


def b64encode_str(s: bytes) -> str:
    return base64.b64encode(s).decode("utf-8")


def read_mapfile(speaker_info_dir: Path) -> dict[str, dict[str, str]]:
    filemap_path = speaker_info_dir / "filemap.json"
    with filemap_path.open(mode="rb") as f:
        filemap: dict[str, dict[str, str]] = json.load(f)
    return filemap


def gen_file_name(filehash: str, filename: str) -> str:
    return f"{filehash}_{filename}"


def file_url(base_url: str, speaker_id: str, filehash: str, filename: str) -> str:
    return f"{base_url}/{speaker_id}/" + gen_file_name(filehash, filename)


def gen_hash_to_resource_id_mapping(
    filemap: dict[str, dict[str, str]]
) -> dict[str, dict[str, str]]:
    return {
        speaker_uuid: {
            f"{filehash}_{basename(filepath)}": filepath
            for filepath, filehash in ph.items()
        }
        for speaker_uuid, ph in filemap.items()
    }


def generate_speaker_router(
    core_manager: CoreManager,
    metas_store: MetasStore,
    root_dir: Path,
) -> APIRouter:
    """話者情報 API Router を生成する"""
    router = APIRouter()

    speaker_info_dir = root_dir / "speaker_info"

    @router.get("/speakers", tags=["その他"])
    def speakers(
        core_version: str | None = None,
    ) -> list[Speaker]:
        speakers = metas_store.load_combined_metas(core_manager.get_core(core_version))
        return filter_speakers_and_styles(speakers, "speaker")

    @router.get("/speaker_info", tags=["その他"])
    def speaker_info(
        self_url: Annotated[str, Depends(get_character_resource_baseurl)],
        speaker_uuid: str,
        resource_url: bool = False,
        core_version: str | None = None,
    ) -> SpeakerInfo:
        """
        指定されたspeaker_uuidに関する情報をjson形式で返します。
        画像や音声はbase64エンコードされたものが返されます。
        """
        return _speaker_info(
            speaker_uuid=speaker_uuid,
            speaker_or_singer="speaker",
            core_version=core_version,
            self_url=self_url,
            resource_url=resource_url,
        )

    mapfile = read_mapfile(speaker_info_dir)

    # FIXME: この関数をどこかに切り出す
    def _speaker_info(
        speaker_uuid: str,
        speaker_or_singer: Literal["speaker", "singer"],
        core_version: str | None,
        self_url: str,
        resource_url: bool,
    ) -> SpeakerInfo:
        # エンジンに含まれる話者メタ情報は、次のディレクトリ構造に従わなければならない：
        # {root_dir}/
        #   speaker_info/
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

        # 該当話者の検索
        speakers = parse_obj_as(
            list[Speaker], json.loads(core_manager.get_core(core_version).speakers)
        )
        speakers = filter_speakers_and_styles(speakers, speaker_or_singer)
        for i in range(len(speakers)):
            if speakers[i].speaker_uuid == speaker_uuid:
                speaker = speakers[i]
                break
        else:
            raise HTTPException(status_code=404, detail="該当する話者が見つかりません")

        try:
            speaker_path = root_dir / "speaker_info" / speaker_uuid
            # 話者情報の取得
            # speaker policy
            policy_path = speaker_path / "policy.md"
            policy = policy_path.read_text("utf-8")
            # speaker portrait
            if resource_url:
                speaker_map = mapfile[speaker_uuid]
                portrait = file_url(
                    self_url,
                    speaker_uuid,
                    speaker_map["portrait.png"],
                    "portrait.png",
                )
            else:
                portrait_path = speaker_path / "portrait.png"
                portrait = b64encode_str(portrait_path.read_bytes())
            # スタイル情報の取得
            style_infos = []
            for style in speaker.styles:
                id = style.id
                # style icon
                style_icon_name = f"{id}.png"
                # style portrait
                style_portrait_name = f"{id}.png"
                style_portrait = None
                # voice samples
                voice_samples_names = [
                    "{}_{}.wav".format(id, str(j + 1).zfill(3)) for j in range(3)
                ]
                if resource_url:
                    icon_hash = speaker_map[f"icons/{style_icon_name}"]
                    icon = file_url(self_url, speaker_uuid, icon_hash, style_icon_name)
                    style_portrait_hash = speaker_map.get(
                        f"portraits/{style_portrait_name}"
                    )
                    if style_portrait_hash is not None:
                        style_portrait = file_url(
                            self_url, speaker_uuid, style_portrait_hash, style_icon_name
                        )
                    voice_samples_hashes = {
                        speaker_map[f"voice_samples/{name}"]: name
                        for name in voice_samples_names
                    }
                    voice_samples = [
                        file_url(self_url, speaker_uuid, k, v)
                        for k, v in voice_samples_hashes.items()
                    ]
                else:
                    style_icon_path = speaker_path / "icons" / style_icon_name
                    icon = b64encode_str(style_icon_path.read_bytes())
                    style_portrait_path = (
                        speaker_path / "portraits" / style_portrait_name
                    )
                    if style_portrait_path.exists():
                        style_portrait = b64encode_str(style_portrait_path.read_bytes())
                    voice_samples = [
                        b64encode_str(
                            (speaker_path / "voice_samples" / name).read_bytes()
                        )
                        for name in voice_samples_names
                    ]
                style_infos.append(
                    {
                        "id": id,
                        "icon": icon,
                        "portrait": style_portrait,
                        "voice_samples": voice_samples,
                    }
                )
        except FileNotFoundError:
            import traceback

            traceback.print_exc()
            raise HTTPException(
                status_code=500, detail="追加情報が見つかりませんでした"
            )

        ret_data = SpeakerInfo(
            policy=policy,
            portrait=portrait,
            style_infos=style_infos,
        )
        return ret_data

    @router.get("/singers", tags=["その他"])
    def singers(
        core_version: str | None = None,
    ) -> list[Speaker]:
        singers = metas_store.load_combined_metas(core_manager.get_core(core_version))
        return filter_speakers_and_styles(singers, "singer")

    @router.get("/singer_info", tags=["その他"])
    def singer_info(
        self_url: Annotated[str, Depends(get_character_resource_baseurl)],
        speaker_uuid: str,
        resource_url: bool = False,
        core_version: str | None = None,
    ) -> SpeakerInfo:
        """
        指定されたspeaker_uuidに関する情報をjson形式で返します。
        画像や音声はbase64エンコードされたものが返されます。
        """
        return _speaker_info(
            speaker_uuid=speaker_uuid,
            speaker_or_singer="singer",
            core_version=core_version,
            self_url=self_url,
            resource_url=resource_url,
        )

    resource_id_mapping = gen_hash_to_resource_id_mapping(mapfile)

    # リソースはAPIとしてアクセスするものではないことを表明するためOpenAPIスキーマーから除外する
    @router.get(
        "/character_resources/{speaker_uuid}/{resource_name}", include_in_schema=False
    )
    async def static(
        request: Request, speaker_uuid: str, resource_name: str
    ) -> Response:
        try:
            resource = resource_id_mapping[speaker_uuid][resource_name]
        except KeyError:
            raise HTTPException(status_code=404)
        headers = {
            "Cache-Control": "max-age=2592000, immutable, stale-while-revalidate"
        }
        response = FileResponse(
            speaker_info_dir / speaker_uuid / resource, headers=headers
        )
        return response

    @router.post("/initialize_speaker", status_code=204, tags=["その他"])
    def initialize_speaker(
        style_id: Annotated[StyleId, Query(alias="speaker")],
        skip_reinit: Annotated[
            bool,
            Query(
                description="既に初期化済みのスタイルの再初期化をスキップするかどうか",
            ),
        ] = False,
        core_version: str | None = None,
    ) -> None:
        """
        指定されたスタイルを初期化します。
        実行しなくても他のAPIは使用できますが、初回実行時に時間がかかることがあります。
        """
        core = core_manager.get_core(core_version)
        core.initialize_style_id_synthesis(style_id, skip_reinit=skip_reinit)

    @router.get("/is_initialized_speaker", tags=["その他"])
    def is_initialized_speaker(
        style_id: Annotated[StyleId, Query(alias="speaker")],
        core_version: str | None = None,
    ) -> bool:
        """
        指定されたスタイルが初期化されているかどうかを返します。
        """
        core = core_manager.get_core(core_version)
        return core.is_initialized_style_id_synthesis(style_id)

    return router
