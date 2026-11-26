"""FastAPI dependencies"""

from collections.abc import Callable, Coroutine, Iterator
from pathlib import Path
from tempfile import TemporaryDirectory, TemporaryFile
from typing import Any, BinaryIO, cast

from fastapi import HTTPException

type VerifyMutabilityAllowed = Callable[[], Coroutine[Any, Any, None]]


def generate_mutability_allowed_verifier(
    disable_mutable_api: bool,
) -> VerifyMutabilityAllowed:
    """verify_mutability_allowed 関数（データ変更の許可を確認する関数）を生成する。"""

    async def verify_mutability_allowed() -> None:
        if disable_mutable_api:
            msg = "エンジンの静的なデータを変更するAPIは無効化されています"
            raise HTTPException(status_code=403, detail=msg)
        else:
            pass

    return verify_mutability_allowed


def get_tempfile() -> Iterator[BinaryIO]:
    """レスポンスを返した後に自動的にcloseされる一時ファイルを作成する。"""
    with TemporaryFile() as f:
        yield cast(BinaryIO, f)


def get_tempdir() -> Iterator[Path]:
    """レスポンスを返した後に自動的に削除される一時ディレクトリを作成する。"""
    with TemporaryDirectory() as td:
        yield Path(td)
