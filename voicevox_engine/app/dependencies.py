"""FastAPI dependencies"""

from typing import Any, Callable, Coroutine, TypeAlias

from fastapi import HTTPException

VerifyMutabilityAllowed: TypeAlias = Callable[[], Coroutine[Any, Any, None]]


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
