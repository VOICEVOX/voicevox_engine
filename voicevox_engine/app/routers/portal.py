"""ポータル機能を提供する API Router"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from voicevox_engine.engine_manifest.EngineManifest import EngineManifest


def generate_portal_router(engine_manifest_data: EngineManifest) -> APIRouter:
    """ポータル API Router を生成する"""
    router = APIRouter()

    @router.get("/", response_class=HTMLResponse, tags=["その他"])
    async def get_portal() -> str:
        """ポータルページを返します。"""
        engine_name = engine_manifest_data.name

        return f"""
        <html>
            <head>
                <title>{engine_name}</title>
            </head>
            <body>
                <h1>{engine_name}</h1>
                {engine_name} へようこそ！
                <ul>
                    <li><a href='/setting'>設定</a></li>
                    <li><a href='/docs'>API ドキュメント</a></li>
        </ul></body></html>
        """

    return router
