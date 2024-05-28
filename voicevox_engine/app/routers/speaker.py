"""話者情報機能を提供する API Router"""

import base64
import json
import traceback
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import parse_obj_as

from voicevox_engine.core.core_initializer import CoreManager
from voicevox_engine.metas.Metas import StyleId
from voicevox_engine.metas.MetasStore import MetasStore, filter_speakers_and_styles
from voicevox_engine.model import Speaker, SpeakerInfo


def b64encode_str(s: bytes) -> str:
    return base64.b64encode(s).decode("utf-8")


def generate_speaker_router(
    core_manager: CoreManager,
    metas_store: MetasStore,
    root_dir: Path,
) -> APIRouter:
    """話者情報 API Router を生成する"""
    router = APIRouter(tags=["その他"])

    @router.get("/speakers")
    def speakers(core_version: str | None = None) -> list[Speaker]:
        """話者情報の一覧を取得します。"""
        speakers = metas_store.load_combined_metas(core_manager.get_core(core_version))
        return filter_speakers_and_styles(speakers, "speaker")

    @router.get("/speaker_info")
    def speaker_info(speaker_uuid: str, core_version: str | None = None) -> SpeakerInfo:
        """
        指定されたspeaker_uuidの話者に関する情報をjson形式で返します。
        画像や音声はbase64エンコードされたものが返されます。
        """
        return _speaker_info(
            speaker_uuid=speaker_uuid,
            speaker_or_singer="speaker",
            core_version=core_version,
        )

    # FIXME: この関数をどこかに切り出す
    def _speaker_info(
        speaker_uuid: str,
        speaker_or_singer: Literal["speaker", "singer"],
        core_version: str | None,
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

        # 該当話者を検索する
        speakers = parse_obj_as(
            list[Speaker], json.loads(core_manager.get_core(core_version).speakers)
        )
        speakers = filter_speakers_and_styles(speakers, speaker_or_singer)
        speaker = next(
            filter(lambda spk: spk.speaker_uuid == speaker_uuid, speakers), None
        )
        if speaker is None:
            raise HTTPException(status_code=404, detail="該当する話者が見つかりません")

        # 話者情報を取得する
        try:
            speaker_path = root_dir / "speaker_info" / speaker_uuid

            # speaker policy
            policy_path = speaker_path / "policy.md"
            policy = policy_path.read_text("utf-8")

            # speaker portrait
            portrait_path = speaker_path / "portrait.png"
            portrait = b64encode_str(portrait_path.read_bytes())

            # スタイル情報を取得する
            style_infos = []
            for style in speaker.styles:
                id = style.id

                # style icon
                style_icon_path = speaker_path / "icons" / f"{id}.png"
                icon = b64encode_str(style_icon_path.read_bytes())

                # style portrait
                style_portrait_path = speaker_path / "portraits" / f"{id}.png"
                style_portrait = None
                if style_portrait_path.exists():
                    style_portrait = b64encode_str(style_portrait_path.read_bytes())

                # voice samples
                voice_samples: list[str] = []
                for j in range(3):
                    num = str(j + 1).zfill(3)
                    voice_path = speaker_path / "voice_samples" / f"{id}_{num}.wav"
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
            traceback.print_exc()
            msg = "追加情報が見つかりませんでした"
            raise HTTPException(status_code=500, detail=msg)

        spk_info = SpeakerInfo(
            policy=policy, portrait=portrait, style_infos=style_infos
        )
        return spk_info

    @router.get("/singers")
    def singers(core_version: str | None = None) -> list[Speaker]:
        """歌手情報の一覧を取得します"""
        singers = metas_store.load_combined_metas(core_manager.get_core(core_version))
        return filter_speakers_and_styles(singers, "singer")

    @router.get("/singer_info")
    def singer_info(speaker_uuid: str, core_version: str | None = None) -> SpeakerInfo:
        """
        指定されたspeaker_uuidの歌手に関する情報をjson形式で返します。
        画像や音声はbase64エンコードされたものが返されます。
        """
        return _speaker_info(
            speaker_uuid=speaker_uuid,
            speaker_or_singer="singer",
            core_version=core_version,
        )

    @router.post("/initialize_speaker", status_code=204)
    def initialize_speaker(
        style_id: Annotated[StyleId, Query(alias="speaker")],
        skip_reinit: Annotated[
            bool,
            Query(
                description="既に初期化済みのスタイルの再初期化をスキップするかどうか"
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

    @router.get("/is_initialized_speaker")
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
