"""OpenAPI schema の設定"""

from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from voicevox_engine.library.model import BaseLibraryInfo, VvlibManifest


def configure_openapi_schema(app: FastAPI) -> FastAPI:
    """自動生成された OpenAPI schema へカスタム属性を追加する。"""

    # BaseLibraryInfo/VvlibManifestモデルはAPIとして表には出ないが、エディタ側で利用したいので、手動で追加する
    # ref: https://fastapi.tiangolo.com/advanced/extending-openapi/#modify-the-openapi-schema
    def custom_openapi() -> Any:
        if app.openapi_schema:
            return app.openapi_schema
        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
            tags=app.openapi_tags,
            servers=app.servers,
            terms_of_service=app.terms_of_service,
            contact=app.contact,
            license_info=app.license_info,
        )
        openapi_schema["components"]["schemas"][
            "VvlibManifest"
        ] = VvlibManifest.schema()
        # ref_templateを指定しない場合、definitionsを参照してしまうので、手動で指定する
        base_library_info = BaseLibraryInfo.schema(
            ref_template="#/components/schemas/{model}"
        )
        # definitionsは既存のモデルを重複して定義するため、不要なので削除
        del base_library_info["definitions"]
        openapi_schema["components"]["schemas"]["BaseLibraryInfo"] = base_library_info
        app.openapi_schema = openapi_schema
        return openapi_schema

    app.openapi = custom_openapi  # type: ignore[method-assign]

    return app
