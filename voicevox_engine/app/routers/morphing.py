"""モーフィング機能を提供する API Router"""

from functools import lru_cache
from tempfile import NamedTemporaryFile
from typing import Annotated, Callable

import soundfile
from fastapi import APIRouter, HTTPException, Query
from starlette.background import BackgroundTask
from starlette.responses import FileResponse

from voicevox_engine.core.core_initializer import Cores
from voicevox_engine.metas.Metas import StyleId
from voicevox_engine.metas.MetasStore import MetasStore, construct_lookup
from voicevox_engine.model import AudioQuery, MorphableTargetInfo, StyleIdNotFoundError
from voicevox_engine.morphing import (
    get_morphable_targets,
    is_synthesis_morphing_permitted,
    synthesis_morphing,
)
from voicevox_engine.morphing import (
    synthesis_morphing_parameter as _synthesis_morphing_parameter,
)
from voicevox_engine.tts_pipeline.tts_engine import TTSEngine
from voicevox_engine.utility.path_utility import delete_file

# キャッシュを有効化
# モジュール側でlru_cacheを指定するとキャッシュを制御しにくいため、HTTPサーバ側で指定する
# TODO: キャッシュを管理するモジュール側API・HTTP側APIを用意する
synthesis_morphing_parameter = lru_cache(maxsize=4)(_synthesis_morphing_parameter)


def generate_morphing_router(
    get_engine: Callable[[str | None], TTSEngine], cores: Cores, metas_store: MetasStore
) -> APIRouter:
    """モーフィング API Router を生成する"""
    router = APIRouter()

    @router.post(
        "/morphable_targets",
        response_model=list[dict[str, MorphableTargetInfo]],
        tags=["音声合成"],
        summary="指定したスタイルに対してエンジン内の話者がモーフィングが可能か判定する",
    )
    def morphable_targets(
        base_style_ids: list[StyleId], core_version: str | None = None
    ) -> list[dict[str, MorphableTargetInfo]]:
        """
        指定されたベーススタイルに対してエンジン内の各話者がモーフィング機能を利用可能か返します。
        モーフィングの許可/禁止は`/speakers`の`speaker.supported_features.synthesis_morphing`に記載されています。
        プロパティが存在しない場合は、モーフィングが許可されているとみなします。
        返り値のスタイルIDはstring型なので注意。
        """
        core = cores.get_core(core_version)

        try:
            speakers = metas_store.load_combined_metas(core=core)
            morphable_targets = get_morphable_targets(
                speakers=speakers, base_style_ids=base_style_ids
            )
            # jsonはint型のキーを持てないので、string型に変換する
            return [
                {str(k): v for k, v in morphable_target.items()}
                for morphable_target in morphable_targets
            ]
        except StyleIdNotFoundError as e:
            raise HTTPException(
                status_code=404,
                detail=f"該当するスタイル(style_id={e.style_id})が見つかりません",
            )

    @router.post(
        "/synthesis_morphing",
        response_class=FileResponse,
        responses={
            200: {
                "content": {
                    "audio/wav": {"schema": {"type": "string", "format": "binary"}}
                },
            }
        },
        tags=["音声合成"],
        summary="2種類のスタイルでモーフィングした音声を合成する",
    )
    def _synthesis_morphing(
        query: AudioQuery,
        base_style_id: Annotated[StyleId, Query(alias="base_speaker")],
        target_style_id: Annotated[StyleId, Query(alias="target_speaker")],
        morph_rate: Annotated[float, Query(ge=0.0, le=1.0)],
        core_version: str | None = None,
    ) -> FileResponse:
        """
        指定された2種類のスタイルで音声を合成、指定した割合でモーフィングした音声を得ます。
        モーフィングの割合は`morph_rate`で指定でき、0.0でベースのスタイル、1.0でターゲットのスタイルに近づきます。
        """
        engine = get_engine(core_version)
        core = cores.get_core(core_version)

        try:
            speakers = metas_store.load_combined_metas(core=core)
            speaker_lookup = construct_lookup(speakers=speakers)
            is_permitted = is_synthesis_morphing_permitted(
                speaker_lookup, base_style_id, target_style_id
            )
            if not is_permitted:
                raise HTTPException(
                    status_code=400,
                    detail="指定されたスタイルペアでのモーフィングはできません",
                )
        except StyleIdNotFoundError as e:
            raise HTTPException(
                status_code=404,
                detail=f"該当するスタイル(style_id={e.style_id})が見つかりません",
            )

        # 生成したパラメータはキャッシュされる
        morph_param = synthesis_morphing_parameter(
            engine=engine,
            core=core,
            query=query,
            base_style_id=base_style_id,
            target_style_id=target_style_id,
        )

        morph_wave = synthesis_morphing(
            morph_param=morph_param,
            morph_rate=morph_rate,
            output_fs=query.outputSamplingRate,
            output_stereo=query.outputStereo,
        )

        with NamedTemporaryFile(delete=False) as f:
            soundfile.write(
                file=f,
                data=morph_wave,
                samplerate=query.outputSamplingRate,
                format="WAV",
            )

        return FileResponse(
            f.name,
            media_type="audio/wav",
            background=BackgroundTask(delete_file, f.name),
        )

    return router
