"""モーフィング機能を提供する API Router"""

import os
from functools import lru_cache
from typing import Annotated, BinaryIO

import soundfile
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic.json_schema import SkipJsonSchema

from voicevox_engine.metas.metas import StyleId
from voicevox_engine.metas.metas_store import MetasStore
from voicevox_engine.model import AudioQuery
from voicevox_engine.morphing.model import MorphableTargetInfo
from voicevox_engine.morphing.morphing import (
    StyleIdNotFoundError,
    get_morphable_targets,
    is_morphable,
    synthesize_morphed_wave,
)
from voicevox_engine.morphing.morphing import (
    synthesis_morphing_parameter as _synthesis_morphing_parameter,
)
from voicevox_engine.tts_pipeline.tts_engine import LATEST_VERSION, TTSEngineManager

from ..dependencies import get_tempfile

# キャッシュを有効化
# モジュール側でlru_cacheを指定するとキャッシュを制御しにくいため、HTTPサーバ側で指定する
# TODO: キャッシュを管理するモジュール側API・HTTP側APIを用意する
synthesis_morphing_parameter = lru_cache(maxsize=4)(_synthesis_morphing_parameter)


def generate_morphing_router(
    tts_engines: TTSEngineManager, metas_store: MetasStore
) -> APIRouter:
    """モーフィング API Router を生成する"""
    router = APIRouter(tags=["音声合成"])

    @router.post(
        "/morphable_targets",
        summary="指定したスタイルに対してエンジン内のキャラクターがモーフィングが可能か判定する",
    )
    def morphable_targets(
        base_style_ids: list[StyleId], core_version: str | SkipJsonSchema[None] = None
    ) -> list[dict[str, MorphableTargetInfo]]:
        """
        指定されたベーススタイルに対してエンジン内の各キャラクターがモーフィング機能を利用可能か返します。

        モーフィングの許可/禁止は`/speakers`の`speaker.supported_features.synthesis_morphing`に記載されています。
        プロパティが存在しない場合は、モーフィングが許可されているとみなします。
        返り値のスタイルIDはstring型なので注意。
        """
        characters = metas_store.characters(core_version)
        try:
            morphable_targets = get_morphable_targets(characters, base_style_ids)
        except StyleIdNotFoundError as e:
            msg = f"該当するスタイル(style_id={e.style_id})が見つかりません"
            raise HTTPException(status_code=404, detail=msg) from e
        # NOTE: jsonはint型のキーを持てないので、string型に変換する
        return [
            {str(k): v for k, v in morphable_target.items()}
            for morphable_target in morphable_targets
        ]

    @router.post(
        "/synthesis_morphing",
        response_class=StreamingResponse,
        responses={
            200: {
                "content": {
                    "audio/wav": {"schema": {"type": "string", "format": "binary"}}
                },
            }
        },
        summary="2種類のスタイルでモーフィングした音声を合成する",
    )
    def _synthesis_morphing(
        query: AudioQuery,
        base_style_id: Annotated[StyleId, Query(alias="base_speaker")],
        target_style_id: Annotated[StyleId, Query(alias="target_speaker")],
        morph_rate: Annotated[float, Query(ge=0.0, le=1.0)],
        temp_file: Annotated[BinaryIO, Depends(get_tempfile)],
        enable_interrogative_upspeak: Annotated[
            bool,
            Query(
                description="疑問系のテキストが与えられたら語尾を自動調整する",
            ),
        ] = True,
        core_version: str | SkipJsonSchema[None] = None,
    ) -> StreamingResponse:
        """
        指定された2種類のスタイルで音声を合成、指定した割合でモーフィングした音声を得ます。

        モーフィングの割合は`morph_rate`で指定でき、0.0でベースのスタイル、1.0でターゲットのスタイルに近づきます。
        """
        version = core_version or LATEST_VERSION
        engine = tts_engines.get_tts_engine(version)

        # モーフィングが許可されないキャラクターペアを拒否する
        characters = metas_store.characters(core_version)
        try:
            morphable = is_morphable(characters, base_style_id, target_style_id)
        except StyleIdNotFoundError as e:
            msg = f"該当するスタイル(style_id={e.style_id})が見つかりません"
            raise HTTPException(status_code=404, detail=msg) from e
        if not morphable:
            msg = "指定されたスタイルペアでのモーフィングはできません"
            raise HTTPException(status_code=400, detail=msg)

        # 生成したパラメータはキャッシュされる
        morph_param = synthesis_morphing_parameter(
            engine=engine,
            query=query,
            base_style_id=base_style_id,
            target_style_id=target_style_id,
            enable_interrogative_upspeak=enable_interrogative_upspeak,
        )

        morph_wave = synthesize_morphed_wave(
            morph_param=morph_param,
            morph_rate=morph_rate,
            output_fs=query.outputSamplingRate,
            output_stereo=query.outputStereo,
        )

        soundfile.write(
            file=temp_file,
            data=morph_wave,
            samplerate=query.outputSamplingRate,
            format="WAV",
        )

        file_size = os.fstat(temp_file.fileno()).st_size
        temp_file.seek(0)

        return StreamingResponse(
            temp_file,
            headers={"content-length": str(file_size)},
            media_type="audio/wav",
        )

    return router
