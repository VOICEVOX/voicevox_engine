"""話者情報機能を提供する API Router"""

from typing import Annotated

from fastapi import APIRouter, Query

from voicevox_engine.core.core_initializer import CoreManager
from voicevox_engine.metas.Metas import Speaker, SpeakerInfo, StyleId
from voicevox_engine.metas.MetasStore import MetasStore, filter_speakers_and_styles


def generate_speaker_router(
    core_manager: CoreManager, metas_store: MetasStore
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
    def speaker_info(speaker_uuid: str, core_version: str | None = None) -> SpeakerInfo:
        """
        指定されたspeaker_uuidの話者に関する情報をjson形式で返します。
        画像や音声はbase64エンコードされたものが返されます。
        """
        return metas_store.speaker_info(
            speaker_uuid=speaker_uuid,
            speaker_or_singer="speaker",
            core_speakers=core_manager.get_core(core_version).speakers,
        )

    @router.get("/singers")
    def singers(core_version: str | None = None) -> list[Speaker]:
        """歌手情報の一覧を取得します"""
        core = core_manager.get_core(core_version)
        singers = metas_store.load_combined_metas(core.speakers)
        return filter_speakers_and_styles(singers, "singer")

    @router.get("/singer_info")
    def singer_info(speaker_uuid: str, core_version: str | None = None) -> SpeakerInfo:
        """
        指定されたspeaker_uuidの歌手に関する情報をjson形式で返します。
        画像や音声はbase64エンコードされたものが返されます。
        """
        return metas_store.speaker_info(
            speaker_uuid=speaker_uuid,
            speaker_or_singer="singer",
            core_speakers=core_manager.get_core(core_version).speakers,
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
