"""グローバルな例外ハンドラの定義と登録"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from voicevox_engine.core.core_initializer import CoreNotFound


def configure_global_exception_handlers(app: FastAPI) -> FastAPI:
    """グローバルな例外ハンドラを app へ設定する。"""

    # 指定されたコアが見つからないエラー
    @app.exception_handler(CoreNotFound)
    async def cnf_exception_handler(request: Request, e: CoreNotFound) -> JSONResponse:
        return JSONResponse(status_code=422, content={"message": f"{str(e)}"})

    return app
