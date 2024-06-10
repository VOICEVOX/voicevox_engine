"""OpenAPI schema の設定"""

from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel

from voicevox_engine.library.model import BaseLibraryInfo, VvlibManifest


def configure_openapi_schema(app: FastAPI, manage_library: bool | None) -> FastAPI:
    """自動生成された OpenAPI schema へカスタム属性を追加する。"""

    # BaseLibraryInfo/VvlibManifestモデルはAPIとして表には出ないが、エディタ側で利用したいので、手動で追加する
    # ref: https://fastapi.tiangolo.com/advanced/extending-openapi/#modify-the-openapi-schema
    def custom_openapi() -> Any:
        if app.openapi_schema:
            return app.openapi_schema
        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            openapi_version=app.openapi_version,
            summary=app.summary,
            description=app.description,
            terms_of_service=app.terms_of_service,
            contact=app.contact,
            license_info=app.license_info,
            routes=app.routes,
            webhooks=app.webhooks.routes,
            tags=app.openapi_tags,
            servers=app.servers,
            separate_input_output_schemas=app.separate_input_output_schemas,
        )
        if manage_library:
            additional_models: list[type[BaseModel]] = [
                BaseLibraryInfo,
                VvlibManifest,
            ]
            for model in additional_models:
                # ref_templateを指定しない場合、definitionsを参照してしまうので、手動で指定する
                schema = model.model_json_schema(
                    ref_template="#/components/schemas/{model}"
                )
                # definitionsは既存のモデルを重複して定義するため、不要なので削除
                if "$defs" in schema:
                    del schema["$defs"]
                openapi_schema["components"]["schemas"][schema["title"]] = schema
        app.openapi_schema = openapi_schema
        return openapi_schema

    app.openapi = custom_openapi  # type: ignore[method-assign]

    return app
