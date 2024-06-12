"""設定機能を提供する API Router"""

from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.templating import Jinja2Templates
from pydantic.json_schema import SkipJsonSchema

from voicevox_engine.engine_manifest import BrandName
from voicevox_engine.setting.model import CorsPolicyMode
from voicevox_engine.setting.setting_manager import SettingHandler
from voicevox_engine.utility.path_utility import resource_root

from ..dependencies import check_disabled_mutable_api

_setting_ui_template = Jinja2Templates(
    directory=resource_root(),
    variable_start_string="<JINJA_PRE>",
    variable_end_string="<JINJA_POST>",
)


def generate_setting_router(
    setting_loader: SettingHandler, brand_name: BrandName
) -> APIRouter:
    """設定 API Router を生成する"""
    router = APIRouter(tags=["設定"])

    @router.get("/setting", response_class=Response)
    def setting_get(request: Request) -> Response:
        """
        設定ページを返します。
        """
        cors_policy_mode, allow_origin = setting_loader.load()

        if allow_origin is None:
            allow_origin = ""

        return _setting_ui_template.TemplateResponse(
            "setting_ui_template.html",
            {
                "request": request,
                "brand_name": brand_name,
                "cors_policy_mode": cors_policy_mode.value,
                "allow_origin": allow_origin,
            },
        )

    @router.post(
        "/setting", status_code=204, dependencies=[Depends(check_disabled_mutable_api)]
    )
    def setting_post(
        cors_policy_mode: Annotated[CorsPolicyMode, Form()],
        allow_origin: Annotated[str | SkipJsonSchema[None], Form()] = None,
    ) -> None:
        """設定を更新します。"""
        setting_loader.save(cors_policy_mode, allow_origin)

    return router
