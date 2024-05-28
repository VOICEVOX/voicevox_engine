"""エンジンの情報機能を提供する API Router"""

import json
from typing import Self

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from voicevox_engine import __version__
from voicevox_engine.core.core_adapter import DeviceSupport
from voicevox_engine.core.core_initializer import CoreManager
from voicevox_engine.engine_manifest.model import EngineManifest


class SupportedDevicesInfo(BaseModel):
    """
    対応しているデバイスの情報
    """

    cpu: bool = Field(title="CPUに対応しているか")
    cuda: bool = Field(title="CUDA(Nvidia GPU)に対応しているか")
    dml: bool = Field(title="DirectML(Nvidia GPU/Radeon GPU等)に対応しているか")

    @classmethod
    def generate_from(cls, device_support: DeviceSupport) -> Self:
        """`DeviceSupport` インスタンスからこのインスタンスを生成する。"""
        return cls(
            cpu=device_support.cpu,
            cuda=device_support.cuda,
            dml=device_support.dml,
        )


def generate_engine_info_router(
    core_manager: CoreManager, engine_manifest_data: EngineManifest
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
            content=json.dumps(core_manager.versions()),
            media_type="application/json",
        )

    @router.get("/supported_devices", response_model=SupportedDevicesInfo)
    def supported_devices(core_version: str | None = None) -> SupportedDevicesInfo:
        """対応デバイスの一覧を取得します。"""
        supported_devices = core_manager.get_core(core_version).supported_devices
        if supported_devices is None:
            raise HTTPException(status_code=422, detail="非対応の機能です。")
        return SupportedDevicesInfo.generate_from(supported_devices)

    @router.get("/engine_manifest", response_model=EngineManifest)
    async def engine_manifest() -> EngineManifest:
        """エンジンマニフェストを取得します。"""
        return engine_manifest_data

    return router
