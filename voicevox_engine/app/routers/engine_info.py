"""エンジンの情報機能を提供する API Router"""

import json
from base64 import b64encode
from typing import Self

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from pydantic.json_schema import SkipJsonSchema

from voicevox_engine import __version__
from voicevox_engine.core.core_adapter import DeviceSupport
from voicevox_engine.core.core_initializer import CoreManager
from voicevox_engine.engine_manifest import (
    BrandName,
    EngineManifestInternal,
    EngineName,
)


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


class UpdateInfo(BaseModel):
    """
    エンジンのアップデート情報
    """

    version: str = Field(title="エンジンのバージョン名")
    descriptions: list[str] = Field(title="アップデートの詳細についての説明")
    contributors: list[str] | SkipJsonSchema[None] = Field(
        default=None, title="貢献者名"
    )


class LicenseInfo(BaseModel):
    """
    依存ライブラリのライセンス情報
    """

    name: str = Field(title="依存ライブラリ名")
    version: str | SkipJsonSchema[None] = Field(
        default=None, title="依存ライブラリのバージョン"
    )
    license: str | SkipJsonSchema[None] = Field(
        default=None, title="依存ライブラリのライセンス名"
    )
    text: str = Field(title="依存ライブラリのライセンス本文")


class SupportedFeatures(BaseModel):
    """
    エンジンが持つ機能の一覧
    """

    adjust_mora_pitch: bool = Field(title="モーラごとの音高の調整")
    adjust_phoneme_length: bool = Field(title="音素ごとの長さの調整")
    adjust_speed_scale: bool = Field(title="全体の話速の調整")
    adjust_pitch_scale: bool = Field(title="全体の音高の調整")
    adjust_intonation_scale: bool = Field(title="全体の抑揚の調整")
    adjust_volume_scale: bool = Field(title="全体の音量の調整")
    interrogative_upspeak: bool = Field(title="疑問文の自動調整")
    synthesis_morphing: bool = Field(
        title="2種類のスタイルでモーフィングした音声を合成"
    )
    sing: bool | SkipJsonSchema[None] = Field(default=None, title="歌唱音声合成")
    manage_library: bool | SkipJsonSchema[None] = Field(
        default=None, title="音声ライブラリのインストール・アンインストール"
    )


class EngineManifest(BaseModel):
    """
    エンジン自体に関する情報
    """

    manifest_version: str = Field(title="マニフェストのバージョン")
    name: EngineName = Field(title="エンジン名")
    brand_name: BrandName = Field(title="ブランド名")
    uuid: str = Field(title="エンジンのUUID")
    url: str = Field(title="エンジンのURL")
    icon: str = Field(title="エンジンのアイコンをBASE64エンコードしたもの")
    default_sampling_rate: int = Field(title="デフォルトのサンプリング周波数")
    frame_rate: float = Field(title="エンジンのフレームレート")
    terms_of_service: str = Field(title="エンジンの利用規約")
    update_infos: list[UpdateInfo] = Field(title="エンジンのアップデート情報")
    dependency_licenses: list[LicenseInfo] = Field(title="依存関係のライセンス情報")
    supported_vvlib_manifest_version: str | SkipJsonSchema[None] = Field(
        default=None, title="エンジンが対応するvvlibのバージョン"
    )
    supported_features: SupportedFeatures = Field(title="エンジンが持つ機能")


def generate_engine_manifest(
    internal_manifest: EngineManifestInternal,
) -> EngineManifest:
    """API 向けのエンジンマニフェストオブジェクトを生成する。"""
    root_dir = internal_manifest.root
    manifest = internal_manifest.model_dump()

    return EngineManifest(
        manifest_version=manifest["manifest_version"],
        name=manifest["name"],
        brand_name=manifest["brand_name"],
        uuid=manifest["uuid"],
        url=manifest["url"],
        default_sampling_rate=manifest["default_sampling_rate"],
        frame_rate=manifest["frame_rate"],
        icon=b64encode((root_dir / manifest["icon"]).read_bytes()).decode("utf-8"),
        terms_of_service=(root_dir / manifest["terms_of_service"]).read_text("utf-8"),
        update_infos=[
            UpdateInfo(**update_info)
            for update_info in json.loads(
                (root_dir / manifest["update_infos"]).read_text("utf-8")
            )
        ],
        # supported_vvlib_manifest_versionを持たないengine_manifestのために
        # キーが存在しない場合はNoneを返すgetを使う
        supported_vvlib_manifest_version=manifest.get(
            "supported_vvlib_manifest_version"
        ),
        dependency_licenses=[
            LicenseInfo(**license_info)
            for license_info in json.loads(
                (root_dir / manifest["dependency_licenses"]).read_text("utf-8")
            )
        ],
        supported_features={
            key: item["value"] for key, item in manifest["supported_features"].items()
        },
    )


def generate_engine_info_router(
    core_manager: CoreManager, engine_manifest_data: EngineManifestInternal
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
        return core_manager.versions()

    @router.get("/supported_devices")
    def supported_devices(
        core_version: str | SkipJsonSchema[None] = None,
    ) -> SupportedDevicesInfo:
        """対応デバイスの一覧を取得します。"""
        supported_devices = core_manager.get_core(core_version).supported_devices
        if supported_devices is None:
            raise HTTPException(status_code=422, detail="非対応の機能です。")
        return SupportedDevicesInfo.generate_from(supported_devices)

    @router.get("/engine_manifest")
    async def engine_manifest() -> EngineManifest:
        """エンジンマニフェストを取得します。"""
        return generate_engine_manifest(engine_manifest_data)

    return router
