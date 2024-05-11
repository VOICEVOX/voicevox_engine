"""エンジンの情報機能を提供する API Router"""

import json

from fastapi import APIRouter, HTTPException, Response

from voicevox_engine import __version__
from voicevox_engine.core.core_initializer import Cores
from voicevox_engine.engine_manifest.EngineManifest import EngineManifest
from voicevox_engine.model import SupportedDevicesInfo


def generate_engine_info_router(
    cores: Cores, engine_manifest_data: EngineManifest
) -> APIRouter:
    """エンジン情報 API Router を生成する"""
    router = APIRouter()

    @router.get("/version", tags=["その他"])
    async def version() -> str:
        return __version__

    @router.get("/core_versions", response_model=list[str], tags=["その他"])
    async def core_versions() -> Response:
        return Response(
            content=json.dumps(cores.versions),
            media_type="application/json",
        )

    @router.get(
        "/supported_devices", response_model=SupportedDevicesInfo, tags=["その他"]
    )
    def supported_devices(
        core_version: str | None = None,
    ) -> Response:
        supported_devices = cores.get_core(core_version).supported_devices
        if supported_devices is None:
            raise HTTPException(status_code=422, detail="非対応の機能です。")
        return Response(
            content=supported_devices,
            media_type="application/json",
        )

    @router.get("/engine_manifest", response_model=EngineManifest, tags=["その他"])
    async def engine_manifest() -> EngineManifest:
        return engine_manifest_data

    return router
