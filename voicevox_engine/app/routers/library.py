"""音声ライブラリ機能を提供する API Router"""

import asyncio
from io import BytesIO
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi import Path as FAPath
from fastapi import Request, Response

from voicevox_engine.library_manager import LibraryManager
from voicevox_engine.model import DownloadableLibraryInfo, InstalledLibraryInfo

from ..dependencies import check_disabled_mutable_api


def generate_library_router(library_manager: LibraryManager) -> APIRouter:
    """音声ライブラリ API Router を生成する"""
    router = APIRouter()

    @router.get(
        "/downloadable_libraries",
        response_description="ダウンロード可能な音声ライブラリの情報リスト",
        tags=["音声ライブラリ管理"],
    )
    def downloadable_libraries() -> list[DownloadableLibraryInfo]:
        """
        ダウンロード可能な音声ライブラリの情報を返します。
        """
        return library_manager.downloadable_libraries()

    @router.get(
        "/installed_libraries",
        response_description="インストールした音声ライブラリの情報",
        tags=["音声ライブラリ管理"],
    )
    def installed_libraries() -> dict[str, InstalledLibraryInfo]:
        """
        インストールした音声ライブラリの情報を返します。
        """
        return library_manager.installed_libraries()

    @router.post(
        "/install_library/{library_uuid}",
        status_code=204,
        tags=["音声ライブラリ管理"],
        dependencies=[Depends(check_disabled_mutable_api)],
    )
    async def install_library(
        library_uuid: Annotated[str, FAPath(description="音声ライブラリのID")],
        request: Request,
    ) -> Response:
        """
        音声ライブラリをインストールします。
        音声ライブラリのZIPファイルをリクエストボディとして送信してください。
        """
        archive = BytesIO(await request.body())
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, library_manager.install_library, library_uuid, archive
        )
        return Response(status_code=204)

    @router.post(
        "/uninstall_library/{library_uuid}",
        status_code=204,
        tags=["音声ライブラリ管理"],
        dependencies=[Depends(check_disabled_mutable_api)],
    )
    def uninstall_library(
        library_uuid: Annotated[str, FAPath(description="音声ライブラリのID")]
    ) -> Response:
        """
        音声ライブラリをアンインストールします。
        """
        library_manager.uninstall_library(library_uuid)
        return Response(status_code=204)

    return router
