"""話者情報機能を提供する API Router"""

from typing import Annotated, Callable

from fastapi import APIRouter, Query

from voicevox_engine.core.core_adapter import CoreAdapter
from voicevox_engine.metas.Metas import StyleId
from voicevox_engine.metas.MetasStore import MetasStore, filter_speakers_and_styles
from voicevox_engine.model import Speaker, SpeakerInfo


def generate_speaker_router(
    get_core: Callable[[str | None], CoreAdapter], metas_store: MetasStore
) -> APIRouter:
    """話者情報 API Router を生成する"""
    router = APIRouter()

    @router.get("/speakers", tags=["その他"])
    def speakers(
        core_version: str | None = None,
    ) -> list[Speaker]:
        speakers = metas_store.load_combined_metas(get_core(core_version))
        return filter_speakers_and_styles(speakers, "speaker")

    @router.get("/speaker_info", tags=["その他"])
    def speaker_info(
        speaker_uuid: str,
        core_version: str | None = None,
    ) -> SpeakerInfo:
        """
        指定されたspeaker_uuidに関する情報をjson形式で返します。
        画像や音声はbase64エンコードされたものが返されます。
        """
        return metas_store.speaker_info(
            speaker_uuid=speaker_uuid,
            speaker_or_singer="speaker",
            core=get_core(core_version),
        )

    @router.get("/singers", tags=["その他"])
    def singers(
        core_version: str | None = None,
    ) -> list[Speaker]:
        singers = metas_store.load_combined_metas(get_core(core_version))
        return filter_speakers_and_styles(singers, "singer")

    @router.get("/singer_info", tags=["その他"])
    def singer_info(
        speaker_uuid: str,
        core_version: str | None = None,
    ) -> SpeakerInfo:
        """
        指定されたspeaker_uuidに関する情報をjson形式で返します。
        画像や音声はbase64エンコードされたものが返されます。
        """
        return metas_store.speaker_info(
            speaker_uuid=speaker_uuid,
            speaker_or_singer="singer",
            core=get_core(core_version),
        )

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
        core = get_core(core_version)
        core.initialize_style_id_synthesis(style_id, skip_reinit=skip_reinit)

    @router.get("/is_initialized_speaker", tags=["その他"])
    def is_initialized_speaker(
        style_id: Annotated[StyleId, Query(alias="speaker")],
        core_version: str | None = None,
    ) -> bool:
        """
        指定されたスタイルが初期化されているかどうかを返します。
        """
        core = get_core(core_version)
        return core.is_initialized_style_id_synthesis(style_id)

    return router
