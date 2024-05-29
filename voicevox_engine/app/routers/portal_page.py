"""ポータルページ機能を提供する API Router"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from voicevox_engine.engine_manifest import EngineName


def generate_portal_page_router(engine_name: EngineName) -> APIRouter:
    """ポータルページ API Router を生成する"""
    router = APIRouter()

    @router.get("/", response_class=HTMLResponse, tags=["その他"])
    async def get_portal_page() -> str:
        """ポータルページを返します。"""
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
