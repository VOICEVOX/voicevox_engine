"""プリセット機能を提供する API Router"""

from traceback import print_exception
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query

from voicevox_engine.preset.model import Preset
from voicevox_engine.preset.preset_manager import (
    PresetInputError,
    PresetInternalError,
    PresetManager,
)

from ..dependencies import VerifyMutabilityAllowed


def generate_preset_router(
    preset_manager: PresetManager, verify_mutability: VerifyMutabilityAllowed
) -> APIRouter:
    """プリセット API Router を生成する"""
    router = APIRouter(tags=["その他"])

    @router.get(
        "/presets",
        response_description="プリセットのリスト",
    )
    def get_presets() -> list[Preset]:
        """エンジンが保持しているプリセットの設定を返します。"""
        try:
            presets = preset_manager.load_presets()
        except PresetInputError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e
        except PresetInternalError as e:
            print_exception(e)
            raise HTTPException(status_code=500) from e
        return presets

    def _add_preset(preset: Preset) -> int:
        try:
            return preset_manager.add_preset(preset)
        except PresetInputError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e
        except PresetInternalError as e:
            print_exception(e)
            raise HTTPException(status_code=500) from e

    def _update_preset(preset: Preset) -> int:
        try:
            return preset_manager.update_preset(preset)
        except PresetInputError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e
        except PresetInternalError as e:
            print_exception(e)
            raise HTTPException(status_code=500) from e

    def _delete_preset(id: int) -> None:
        try:
            preset_manager.delete_preset(id)
        except PresetInputError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e
        except PresetInternalError as e:
            print_exception(e)
            raise HTTPException(status_code=500) from e

    @router.post(
        "/presets",
        response_description="追加したプリセットのプリセットID",
        dependencies=[Depends(verify_mutability)],
    )
    def create_preset(
        preset: Annotated[
            Preset,
            Body(
                description="新しいプリセット。プリセットIDが既存のものと重複している場合は、新規のプリセットIDが採番されます。"
            ),
        ],
    ) -> int:
        """新しいプリセットを追加します。"""
        return _add_preset(preset)

    @router.put(
        "/presets/{preset_id}",
        status_code=204,
        dependencies=[Depends(verify_mutability)],
    )
    def replace_preset(
        preset_id: Annotated[int, Path(description="更新するプリセットのプリセットID")],
        preset: Annotated[
            Preset,
            Body(
                description="更新するプリセット。プリセットIDがパスのプリセットIDと一致している必要があります。"
            ),
        ],
    ) -> None:
        """既存のプリセットを更新します。"""
        if preset.id != preset_id:
            raise HTTPException(
                status_code=422,
                detail="パスのプリセットIDとプリセットのIDが一致しません",
            )
        _update_preset(preset)

    @router.delete(
        "/presets/{preset_id}",
        status_code=204,
        dependencies=[Depends(verify_mutability)],
    )
    def remove_preset(
        preset_id: Annotated[int, Path(description="削除するプリセットのプリセットID")],
    ) -> None:
        """既存のプリセットを削除します。"""
        _delete_preset(preset_id)

    @router.post(
        "/add_preset",
        response_description="追加したプリセットのプリセットID",
        dependencies=[Depends(verify_mutability)],
        deprecated=True,
    )
    def add_preset(
        preset: Annotated[
            Preset,
            Body(
                description="新しいプリセット。プリセットIDが既存のものと重複している場合は、新規のプリセットIDが採番されます。"
            ),
        ],
    ) -> int:
        """新しいプリセットを追加します。代わりに `POST /presets` を利用してください。"""
        return _add_preset(preset)

    @router.post(
        "/update_preset",
        response_description="更新したプリセットのプリセットID",
        dependencies=[Depends(verify_mutability)],
        deprecated=True,
    )
    def update_preset(
        preset: Annotated[
            Preset,
            Body(
                description="更新するプリセット。プリセットIDが更新対象と一致している必要があります。"
            ),
        ],
    ) -> int:
        """既存のプリセットを更新します。代わりに `PUT /presets/{preset_id}` を利用してください。"""
        return _update_preset(preset)

    @router.post(
        "/delete_preset",
        status_code=204,
        dependencies=[Depends(verify_mutability)],
        deprecated=True,
    )
    def delete_preset(
        id: Annotated[int, Query(description="削除するプリセットのプリセットID")],
    ) -> None:
        """既存のプリセットを削除します。代わりに `DELETE /presets/{preset_id}` を利用してください。"""
        _delete_preset(id)

    return router
