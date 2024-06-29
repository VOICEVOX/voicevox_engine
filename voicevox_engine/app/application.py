"""ASGI application の生成"""

from pathlib import Path

from fastapi import FastAPI

from voicevox_engine import __version__
from voicevox_engine.app.dependencies import generate_mutability_allowed_verifier
from voicevox_engine.app.global_exceptions import configure_global_exception_handlers
from voicevox_engine.app.middlewares import configure_middlewares
from voicevox_engine.app.openapi_schema import configure_openapi_schema
from voicevox_engine.app.routers.character import generate_character_router
from voicevox_engine.app.routers.engine_info import generate_engine_info_router
from voicevox_engine.app.routers.library import generate_library_router
from voicevox_engine.app.routers.morphing import generate_morphing_router
from voicevox_engine.app.routers.portal_page import generate_portal_page_router
from voicevox_engine.app.routers.preset import generate_preset_router
from voicevox_engine.app.routers.setting import generate_setting_router
from voicevox_engine.app.routers.tts_pipeline import generate_tts_pipeline_router
from voicevox_engine.app.routers.user_dict import generate_user_dict_router
from voicevox_engine.cancellable_engine import CancellableEngine
from voicevox_engine.core.core_adapter import CoreCharacter
from voicevox_engine.core.core_initializer import CoreManager
from voicevox_engine.engine_manifest import EngineManifest
from voicevox_engine.library.library_manager import LibraryManager
from voicevox_engine.metas.MetasStore import MetasStore
from voicevox_engine.preset.preset_manager import PresetManager
from voicevox_engine.resource_manager import ResourceManager
from voicevox_engine.setting.model import CorsPolicyMode
from voicevox_engine.setting.setting_manager import SettingHandler
from voicevox_engine.tts_pipeline.tts_engine import TTSEngineManager
from voicevox_engine.user_dict.user_dict_manager import UserDictionary
from voicevox_engine.utility.path_utility import engine_root
from voicevox_engine.utility.runtime_utility import is_development


def generate_app(
    tts_engines: TTSEngineManager,
    core_manager: CoreManager,
    setting_loader: SettingHandler,
    preset_manager: PresetManager,
    user_dict: UserDictionary,
    engine_manifest: EngineManifest,
    library_manager: LibraryManager,
    cancellable_engine: CancellableEngine | None = None,
    character_info_dir: Path | None = None,
    cors_policy_mode: CorsPolicyMode = CorsPolicyMode.localapps,
    allow_origin: list[str] | None = None,
    disable_mutable_api: bool = False,
) -> FastAPI:
    """ASGI 'application' 仕様に準拠した VOICEVOX ENGINE アプリケーションインスタンスを生成する。"""
    if character_info_dir is None:
        character_info_dir = engine_root() / "resources" / "character_info"

    verify_mutability_allowed = generate_mutability_allowed_verifier(
        disable_mutable_api
    )

    app = FastAPI(
        title=engine_manifest.name,
        description=f"{engine_manifest.brand_name} の音声合成エンジンです。",
        version=__version__,
        separate_input_output_schemas=False,  # Pydantic V1 のときのスキーマに合わせるため
    )
    app = configure_middlewares(app, cors_policy_mode, allow_origin)
    app = configure_global_exception_handlers(app)

    resource_manager = ResourceManager(is_development())
    resource_manager.register_dir(character_info_dir)

    core_version_list = core_manager.versions()

    def _get_core_characters(version: str | None) -> list[CoreCharacter]:
        version = version or core_manager.latest_version()
        core = core_manager.get_core(version)
        return core.characters

    metas_store = MetasStore(
        character_info_dir,
        _get_core_characters,
        resource_manager,
    )

    app.include_router(
        generate_tts_pipeline_router(tts_engines, preset_manager, cancellable_engine)
    )
    app.include_router(generate_morphing_router(tts_engines, metas_store))
    app.include_router(
        generate_preset_router(preset_manager, verify_mutability_allowed)
    )
    app.include_router(generate_character_router(resource_manager, metas_store))
    if engine_manifest.supported_features.manage_library:
        app.include_router(
            generate_library_router(library_manager, verify_mutability_allowed)
        )
    app.include_router(generate_user_dict_router(user_dict, verify_mutability_allowed))
    app.include_router(generate_engine_info_router(core_version_list, engine_manifest))
    app.include_router(
        generate_setting_router(
            setting_loader, engine_manifest.brand_name, verify_mutability_allowed
        )
    )
    app.include_router(generate_portal_page_router(engine_manifest.name))

    app = configure_openapi_schema(
        app, engine_manifest.supported_features.manage_library
    )

    return app
