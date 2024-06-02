"""グローバルな例外ハンドラの定義と登録"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from voicevox_engine.core.core_initializer import CoreNotFound
from voicevox_engine.tts_pipeline.tts_engine import EngineNotFound


def configure_global_exception_handlers(app: FastAPI) -> FastAPI:
    """グローバルな例外ハンドラを app へ設定する。"""

    # 指定されたコアが見つからないエラー
    @app.exception_handler(CoreNotFound)
    async def cnf_exception_handler(request: Request, e: CoreNotFound) -> JSONResponse:
        return JSONResponse(status_code=422, content={"message": f"{str(e)}"})

    # 指定されたエンジンが見つからないエラー
    @app.exception_handler(EngineNotFound)
    async def enf_exception_handler(
        request: Request, e: EngineNotFound
    ) -> JSONResponse:
        # NOTE: EngineNotFound は CoreNotFound 以外でも起きうる。
        #       しかしコアが無いケースが大半であるため、ユーザーの問題解決を助ける観点から情報を付与している。
        msg = f"{str(e)}。当該バージョンのコアが存在しない可能性があります。"
        return JSONResponse(status_code=422, content={"message": msg})

    return app
