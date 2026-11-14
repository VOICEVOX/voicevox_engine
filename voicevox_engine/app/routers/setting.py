"""設定機能を提供する API Router"""

from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader
from pydantic.json_schema import SkipJsonSchema

from voicevox_engine.engine_manifest import BrandName
from voicevox_engine.setting.model import CorsPolicyMode
from voicevox_engine.setting.setting_manager import Setting, SettingHandler
from voicevox_engine.utility.path_utility import resource_root

from ..dependencies import VerifyMutabilityAllowed

_setting_ui_template = Jinja2Templates(
    env=Environment(
        variable_start_string="<JINJA_PRE>",
        variable_end_string="<JINJA_POST>",
        loader=FileSystemLoader(resource_root()),
    ),
)


def generate_setting_router(
    setting_loader: SettingHandler,
    brand_name: BrandName,
    verify_mutability: VerifyMutabilityAllowed,
    applied_cors_policy_mode: CorsPolicyMode,
    applied_allow_origin: list[str] | None,
) -> APIRouter:
    """
    設定 API Router を生成する

    `applied_*` はエンジン起動時に実際に適用された値。起動引数が設定ファイルより優先されるため、設定ファイルの値と異なることがある。
    """
    router = APIRouter(tags=["設定"])

    @router.get("/setting", response_class=Response)
    def setting_get(request: Request) -> Response:
        """設定ページを返します。"""
        settings = setting_loader.load()

        cors_policy_mode = settings.cors_policy_mode
        allow_origin = settings.allow_origin

        if allow_origin is None:
            allow_origin = ""

        return _setting_ui_template.TemplateResponse(
            request=request,
            name="setting_ui_template.html",
            context={
                "brand_name": brand_name,
                "cors_policy_mode": cors_policy_mode.value,
                "allow_origin": allow_origin,
                "applied_cors_policy_mode": applied_cors_policy_mode.value,
                "applied_allow_origin": " ".join(applied_allow_origin or []),
            },
        )

    @router.post("/setting", status_code=204, dependencies=[Depends(verify_mutability)])
    def setting_post(
        cors_policy_mode: Annotated[CorsPolicyMode, Form()],
        allow_origin: Annotated[str | SkipJsonSchema[None], Form()] = None,
    ) -> None:
        """設定を更新します。"""
        settings = Setting(
            cors_policy_mode=cors_policy_mode,
            allow_origin=allow_origin,
        )

        # 更新した設定へ上書き
        setting_loader.save(settings)

    return router
