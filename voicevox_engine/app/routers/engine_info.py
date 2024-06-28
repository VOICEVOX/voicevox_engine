"""エンジンの情報機能を提供する API Router"""

from typing import Self

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from pydantic.json_schema import SkipJsonSchema

from voicevox_engine import __version__
from voicevox_engine.core.core_adapter import DeviceSupport
from voicevox_engine.core.core_initializer import CoreManager
from voicevox_engine.engine_manifest import EngineManifest
from voicevox_engine.tts_pipeline.tts_engine import LATEST_VERSION, TTSEngineManager


class SupportedDevicesInfo(BaseModel):
    """
    対応しているデバイスの情報
    """

    cpu: bool = Field(description="CPUに対応しているか")
    cuda: bool = Field(description="CUDA(Nvidia GPU)に対応しているか")
    dml: bool = Field(description="DirectML(Nvidia GPU/Radeon GPU等)に対応しているか")

    @classmethod
    def generate_from(cls, device_support: DeviceSupport) -> Self:
        """`DeviceSupport` インスタンスからこのインスタンスを生成する。"""
        return cls(
            cpu=device_support.cpu,
            cuda=device_support.cuda,
            dml=device_support.dml,
        )


def generate_engine_info_router(
    core_version_list: list[str],
    tts_engine_manager: TTSEngineManager,
    engine_manifest_data: EngineManifest,
) -> APIRouter:
    """エンジン情報 API Router を生成する"""
    router = APIRouter(tags=["その他"])

    @router.get("/version")
    async def version() -> str:
        """エンジンのバージョンを取得します。"""
        return __version__

    @router.get("/core_versions")
    async def core_versions() -> list[str]:
        """利用可能なコアのバージョン一覧を取得します。"""
        return core_version_list

    @router.get("/supported_devices")
    def supported_devices(
        core_version: str | SkipJsonSchema[None] = None,
    ) -> SupportedDevicesInfo:
        """対応デバイスの一覧を取得します。"""
        version = core_version or LATEST_VERSION
        supported_devices = tts_engine_manager.get_engine(version).supported_devices
        if supported_devices is None:
            raise HTTPException(status_code=422, detail="非対応の機能です。")
        return SupportedDevicesInfo.generate_from(supported_devices)

    @router.get("/engine_manifest")
    async def engine_manifest() -> EngineManifest:
        """エンジンマニフェストを取得します。"""
        return engine_manifest_data

    return router
