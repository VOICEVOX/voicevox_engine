from dataclasses import dataclass

from fastapi import HTTPException


# 許可されていないAPIを無効化する
@dataclass
class MutableAPI:
    enable: bool = True


mutable_api = MutableAPI()


async def check_disabled_mutable_api() -> None:
    if not mutable_api.enable:
        raise HTTPException(
            status_code=403,
            detail="エンジンの静的なデータを変更するAPIは無効化されています",
        )
