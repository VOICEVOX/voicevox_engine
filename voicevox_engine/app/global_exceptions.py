"""グローバルな例外ハンドラの定義と登録"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from voicevox_engine.core.core_initializer import CoreNotFound
from voicevox_engine.tts_pipeline.tts_engine import (
    MockTTSEngineNotFound,
    TTSEngineNotFound,
)


def configure_global_exception_handlers(app: FastAPI) -> FastAPI:
    """グローバルな例外ハンドラを app へ設定する。"""

    # 指定されたコアが見つからないエラー
    @app.exception_handler(CoreNotFound)
    async def cnf_exception_handler(request: Request, e: CoreNotFound) -> JSONResponse:
        return JSONResponse(status_code=422, content={"message": f"{str(e)}"})

    # 指定されたエンジンが見つからないエラー
    @app.exception_handler(TTSEngineNotFound)
    async def no_engine_exception_handler(
        request: Request, e: TTSEngineNotFound
    ) -> JSONResponse:
        msg = f"バージョン {e.version} のコアが見つかりません。"
        return JSONResponse(status_code=422, content={"message": msg})

    # 指定されたモック版エンジンが見つからないエラー
    @app.exception_handler(MockTTSEngineNotFound)
    async def no_mock_exception_handler(
        request: Request, e: MockTTSEngineNotFound
    ) -> JSONResponse:
        msg = "モックが見つかりません。エンジンの起動引数 `--enable_mock` を確認してください。"
        return JSONResponse(status_code=422, content={"message": msg})

    return app
