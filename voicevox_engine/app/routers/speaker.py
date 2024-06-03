"""話者情報機能を提供する API Router"""

import base64
import json
from hashlib import sha256
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, Response
from pydantic import parse_obj_as

from voicevox_engine.core.core_initializer import CoreManager
from voicevox_engine.metas.Metas import Speaker, SpeakerInfo
from voicevox_engine.metas.MetasStore import MetasStore, filter_speakers_and_styles

RESOURCE_ENDPOINT = "resources"


async def get_resource_baseurl(request: Request) -> str:
    return f"{request.url.scheme}://{request.url.netloc}/{RESOURCE_ENDPOINT}"


def b64encode_str(s: bytes) -> str:
    return base64.b64encode(s).decode("utf-8")


class SpeakerResourceManager:
    def __init__(self, speaker_info_dir: Path, is_development: bool) -> None:
        try:
            with (speaker_info_dir.parent / "filemap.json").open(mode="rb") as f:
                data: dict[str, str] = json.load(f)
            self.filemap = {speaker_info_dir / k: v for k, v in data.items()}
        except FileNotFoundError as e:
            if is_development:
                self.filemap = {
                    i: sha256(i.read_bytes()).digest().hex()
                    for i in speaker_info_dir.glob("**/*")
                    if i.is_file()
                }
            else:
                raise e
        self.hashmap = {v: k for k, v in self.filemap.items()}

    def resource_str(
        self,
        resource_path: Path,
        base_url: str,
        resource_format: Literal["base64", "url"],
    ) -> str:
        if resource_format == "base64":
            return b64encode_str(resource_path.read_bytes())
        return f"{base_url}/{self.filemap[resource_path]}"

    def resource_path(self, filehash: str) -> Path:
        return self.hashmap[filehash]


def generate_speaker_router(
    core_manager: CoreManager,
    metas_store: MetasStore,
    speaker_info_dir: Path,
) -> APIRouter:
    """話者情報 API Router を生成する"""
    router = APIRouter(tags=["その他"])

    @router.get("/speakers")
    def speakers(core_version: str | None = None) -> list[Speaker]:
        """話者情報の一覧を取得します。"""
        core = core_manager.get_core(core_version)
        speakers = metas_store.load_combined_metas(core.speakers)
        return filter_speakers_and_styles(speakers, "speaker")

    @router.get("/speaker_info")
    def speaker_info(
        self_url: Annotated[str, Depends(get_resource_baseurl)],
        speaker_uuid: str,
        resource_format: Literal["base64", "url"] = "base64",
        core_version: str | None = None,
    ) -> SpeakerInfo:
        """
        指定されたspeaker_uuidの話者に関する情報をjson形式で返します。
        画像や音声はbase64エンコードされたものが返されます。
        """
        return _speaker_info(
            speaker_uuid=speaker_uuid,
            speaker_or_singer="speaker",
            core_version=core_version,
            self_url=self_url,
            resource_format=resource_format,
        )

    manager = SpeakerResourceManager(speaker_info_dir, True)

    # FIXME: この関数をどこかに切り出す
    def _speaker_info(
        speaker_uuid: str,
        speaker_or_singer: Literal["speaker", "singer"],
        core_version: str | None,
        self_url: str,
        resource_format: Literal["base64", "url"],
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
        speakers = parse_obj_as(
            list[Speaker], core_manager.get_core(core_version).speakers
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

            # speaker portrait
            portrait_path = speaker_path / "portrait.png"
            portrait = manager.resource_str(portrait_path, self_url, resource_format)

            # スタイル情報を取得する
            style_infos = []
            for style in speaker.styles:
                id = style.id

                # style icon
                style_icon_path = speaker_path / "icons" / f"{id}.png"
                icon = manager.resource_str(style_icon_path, self_url, resource_format)

                # style portrait
                style_portrait_path = speaker_path / "portraits" / f"{id}.png"
                style_portrait = None
                if style_portrait_path.exists():
                    style_portrait = manager.resource_str(
                        style_portrait_path, self_url, resource_format
                    )

                # voice samples
                voice_samples: list[str] = []
                for j in range(3):
                    num = str(j + 1).zfill(3)
                    voice_path = speaker_path / "voice_samples" / f"{id}_{num}.wav"
                    voice_samples.append(
                        manager.resource_str(voice_path, self_url, resource_format)
                    )

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

        spk_info = SpeakerInfo(
            policy=policy, portrait=portrait, style_infos=style_infos
        )
        return spk_info

    @router.get("/singers")
    def singers(core_version: str | None = None) -> list[Speaker]:
        """歌手情報の一覧を取得します"""
        core = core_manager.get_core(core_version)
        singers = metas_store.load_combined_metas(core.speakers)
        return filter_speakers_and_styles(singers, "singer")

    @router.get("/singer_info")
    def singer_info(
        self_url: Annotated[str, Depends(get_resource_baseurl)],
        speaker_uuid: str,
        resource_format: Literal["base64", "url"] = "base64",
        core_version: str | None = None,
    ) -> SpeakerInfo:
        """
        指定されたspeaker_uuidの歌手に関する情報をjson形式で返します。
        画像や音声はbase64エンコードされたものが返されます。
        """
        return _speaker_info(
            speaker_uuid=speaker_uuid,
            speaker_or_singer="singer",
            core_version=core_version,
            self_url=self_url,
            resource_format=resource_format,
        )

    # リソースはAPIとしてアクセスするものではないことを表明するためOpenAPIスキーマーから除外する
    @router.get(f"/{RESOURCE_ENDPOINT}/{{resource_name}}", include_in_schema=False)
    async def resources(request: Request, resource_name: str) -> Response:
        headers = {
            "Cache-Control": "max-age=2592000, immutable, stale-while-revalidate"
        }
        resource_path = manager.resource_path(resource_name)
        response = FileResponse(resource_path, headers=headers)
        return response

    return router
