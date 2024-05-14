"""エンジンの情報機能を提供する API Router"""

import json
from typing import Callable

from fastapi import APIRouter, HTTPException, Response

from voicevox_engine import __version__
from voicevox_engine.core.core_adapter import CoreAdapter
from voicevox_engine.engine_manifest.EngineManifest import EngineManifest
from voicevox_engine.model import SupportedDevicesInfo


def generate_engine_info_router(
    get_core: Callable[[str | None], CoreAdapter],
    cores: dict[str, CoreAdapter],
    engine_manifest_data: EngineManifest,
) -> APIRouter:
    """エンジン情報 API Router を生成する"""
    router = APIRouter(tags=["その他"])

    @router.get("/version")
    async def version() -> str:
        """エンジンのバージョンを取得します。"""
        return __version__

    @router.get("/core_versions", response_model=list[str])
    async def core_versions() -> Response:
        """利用可能なコアのバージョン一覧を取得します。"""
        return Response(
            content=json.dumps(list(cores.keys())),
            media_type="application/json",
        )

    @router.get("/supported_devices", response_model=SupportedDevicesInfo)
    def supported_devices(core_version: str | None = None) -> Response:
        """対応デバイスの一覧を取得します。"""
        supported_devices = get_core(core_version).supported_devices
        if supported_devices is None:
            raise HTTPException(status_code=422, detail="非対応の機能です。")
        return Response(
            content=supported_devices,
            media_type="application/json",
        )

    @router.get("/engine_manifest", response_model=EngineManifest)
    async def engine_manifest() -> EngineManifest:
        """エンジンマニフェストを取得します。"""
        return engine_manifest_data

    return router
