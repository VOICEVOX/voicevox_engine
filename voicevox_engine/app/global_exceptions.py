"""グローバルな例外ハンドラの定義と登録"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from voicevox_engine.core.core_initializer import MOCK_VER, CoreNotFound
from voicevox_engine.tts_pipeline.tts_engine import TTSEngineNotFound


def configure_global_exception_handlers(app: FastAPI) -> FastAPI:
    """グローバルな例外ハンドラを app へ設定する。"""

    # 指定されたコアが見つからないエラー
    @app.exception_handler(CoreNotFound)
    async def cnf_exception_handler(request: Request, e: CoreNotFound) -> JSONResponse:
        return JSONResponse(status_code=422, content={"message": f"{str(e)}"})

    # 指定されたエンジンが見つからないエラー
    @app.exception_handler(TTSEngineNotFound)
    async def enf_exception_handler(
        request: Request, e: TTSEngineNotFound
    ) -> JSONResponse:
        version = e.version
        if version == MOCK_VER:
            msg = "コアのモックが見つかりません。エンジンの起動引数 `--enable_mock` を確認してください。"
        elif version == "latest":
            msg = "コアが1つも見つかりません。"
        else:
            msg = f"バージョン {version} のコアが見つかりません。"
        return JSONResponse(status_code=422, content={"message": msg})

    return app
