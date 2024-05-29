from typing import Any, Callable, Coroutine, TypeAlias

from fastapi import HTTPException

VerifyMutability: TypeAlias = Callable[[], Coroutine[Any, Any, None]]


def generate_verify_mutability(disable_mutable_api: bool) -> VerifyMutability:
    """verify_mutability 関数（データ変更の許可を確認する関数）を生成する。"""

    async def verify_mutability() -> None:
        if disable_mutable_api:
            msg = "エンジンの静的なデータを変更するAPIは無効化されています"
            raise HTTPException(status_code=403, detail=msg)
        else:
            pass

    return verify_mutability
