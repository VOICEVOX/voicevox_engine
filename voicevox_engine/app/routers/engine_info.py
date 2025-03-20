"""エンジンの情報機能を提供する API Router"""

from fastapi import APIRouter

from voicevox_engine import __version__
from voicevox_engine.engine_manifest import EngineManifest


def generate_engine_info_router(
    core_version_list: list[str], engine_manifest_data: EngineManifest
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

    @router.get("/engine_manifest")
    async def engine_manifest() -> EngineManifest:
        """エンジンマニフェストを取得します。"""
        return engine_manifest_data

    return router
