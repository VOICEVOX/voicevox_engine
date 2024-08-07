"""音声ライブラリ機能を提供する API Router"""

import asyncio
from io import BytesIO
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request

from voicevox_engine.library.library_manager import (
    LibraryFormatInvalidError,
    LibraryInternalError,
    LibraryManager,
    LibraryNotFoundError,
    LibraryOperationUnauthorizedError,
    LibraryUnsupportedError,
)
from voicevox_engine.library.model import DownloadableLibraryInfo, InstalledLibraryInfo

from ..dependencies import VerifyMutabilityAllowed


def generate_library_router(
    library_manager: LibraryManager, verify_mutability: VerifyMutabilityAllowed
) -> APIRouter:
    """音声ライブラリ API Router を生成する"""
    router = APIRouter(tags=["音声ライブラリ管理"])

    @router.get(
        "/downloadable_libraries",
        response_description="ダウンロード可能な音声ライブラリの情報リスト",
    )
    def downloadable_libraries() -> list[DownloadableLibraryInfo]:
        """
        ダウンロード可能な音声ライブラリの情報を返します。
        """
        return library_manager.downloadable_libraries()

    @router.get(
        "/installed_libraries",
        response_description="インストールした音声ライブラリの情報",
    )
    def installed_libraries() -> dict[str, InstalledLibraryInfo]:
        """
        インストールした音声ライブラリの情報を返します。
        """
        return library_manager.installed_libraries()

    @router.post(
        "/install_library/{library_uuid}",
        status_code=204,
        dependencies=[Depends(verify_mutability)],
    )
    async def install_library(
        library_uuid: Annotated[str, Path(description="音声ライブラリのID")],
        request: Request,
    ) -> None:
        """
        音声ライブラリをインストールします。
        音声ライブラリのZIPファイルをリクエストボディとして送信してください。
        """
        archive = BytesIO(await request.body())
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(
                None, library_manager.install_library, library_uuid, archive
            )
        except LibraryNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except LibraryFormatInvalidError as e:
            raise HTTPException(status_code=422, detail=str(e))
        except LibraryUnsupportedError as e:
            raise HTTPException(status_code=422, detail=str(e))
        except LibraryOperationUnauthorizedError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except LibraryInternalError as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post(
        "/uninstall_library/{library_uuid}",
        status_code=204,
        dependencies=[Depends(verify_mutability)],
    )
    def uninstall_library(
        library_uuid: Annotated[str, Path(description="音声ライブラリのID")]
    ) -> None:
        """
        音声ライブラリをアンインストールします。
        """
        try:
            library_manager.uninstall_library(library_uuid)
        except LibraryNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except LibraryFormatInvalidError as e:
            raise HTTPException(status_code=422, detail=str(e))
        except LibraryUnsupportedError as e:
            raise HTTPException(status_code=422, detail=str(e))
        except LibraryOperationUnauthorizedError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except LibraryInternalError as e:
            raise HTTPException(status_code=500, detail=str(e))

    return router
