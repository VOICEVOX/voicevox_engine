"""グローバルな例外ハンドラの定義と登録"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from voicevox_engine.tts_pipeline.tts_engine import EngineNotFound


def register_global_exception_handlers(app: FastAPI) -> FastAPI:
    """グローバルな例外ハンドラを app へ登録する。"""

    # エンジンは複数 router 内で呼ばれるためグローバルなハンドラが相応しい
    @app.exception_handler(EngineNotFound)
    async def enf_exception_handler(request: Request, e: EngineNotFound) -> JSONResponse:
        return JSONResponse(status_code=422, content={"message": f"{str(e)}"})

    return app