"""FastAPI dependencies"""

from collections.abc import Callable, Coroutine
from typing import Annotated, Any

from fastapi import Depends, HTTPException
from pydantic.json_schema import SkipJsonSchema

from voicevox_engine.tts_pipeline.song_engine import SongEngine, SongEngineManager
from voicevox_engine.tts_pipeline.tts_engine import (
    LATEST_VERSION,
    TTSEngine,
    TTSEngineManager,
)

type VerifyMutabilityAllowed = Callable[[], Coroutine[Any, Any, None]]
type GetTTSEngine = Callable[[str | None], Coroutine[Any, Any, TTSEngine]]
type GetSongEngine = Callable[[str | None], Coroutine[Any, Any, SongEngine]]


def generate_mutability_allowed_verifier(
    disable_mutable_api: bool,
) -> VerifyMutabilityAllowed:
    """verify_mutability_allowed 関数（データ変更の許可を確認する関数）を生成する。"""

    async def verify_mutability_allowed() -> None:
        if disable_mutable_api:
            msg = "エンジンの静的なデータを変更するAPIは無効化されています"
            raise HTTPException(status_code=403, detail=msg)
        else:
            pass

    return verify_mutability_allowed


async def get_core_version(
    core_version: str | SkipJsonSchema[None] = None,
) -> str | None:
    """`core_version`を取得する"""
    return core_version


def generate_tts_engine_getter(tts_engines: TTSEngineManager) -> GetTTSEngine:
    """get_tts_engine 関数(`tts_engine`を取得する関数）を生成する。"""

    async def get_tts_engine(
        core_version: Annotated[str | None, Depends(get_core_version)],
    ) -> TTSEngine:
        version = core_version or LATEST_VERSION
        return tts_engines.get_tts_engine(version)

    return get_tts_engine


def generate_song_engine_getter(song_engines: SongEngineManager) -> GetSongEngine:
    """get_song_engine 関数(`song_engine`を取得する関数）を生成する。"""

    async def get_song_engine(
        core_version: Annotated[str | None, Depends(get_core_version)],
    ) -> SongEngine:
        version = core_version or LATEST_VERSION
        return song_engines.get_song_engine(version)

    return get_song_engine
