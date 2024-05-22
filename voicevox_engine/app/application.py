from pathlib import Path

from fastapi import FastAPI

from voicevox_engine import __version__
from voicevox_engine.app.dependencies import deprecated_mutable_api
from voicevox_engine.app.middlewares import configure_middlewares
from voicevox_engine.app.openapi_schema import configure_openapi_schema
from voicevox_engine.app.routers.engine_info import generate_engine_info_router
from voicevox_engine.app.routers.library import generate_library_router
from voicevox_engine.app.routers.morphing import generate_morphing_router
from voicevox_engine.app.routers.portal_page import generate_portal_page_router
from voicevox_engine.app.routers.preset import generate_preset_router
from voicevox_engine.app.routers.setting import generate_setting_router
from voicevox_engine.app.routers.speaker import generate_speaker_router
from voicevox_engine.app.routers.tts_pipeline import generate_tts_pipeline_router
from voicevox_engine.app.routers.user_dict import generate_user_dict_router
from voicevox_engine.cancellable_engine import CancellableEngine
from voicevox_engine.core.core_initializer import CoreManager
from voicevox_engine.engine_manifest.EngineManifest import EngineManifest
from voicevox_engine.library_manager import LibraryManager
from voicevox_engine.metas.MetasStore import MetasStore
from voicevox_engine.preset.PresetManager import PresetManager
from voicevox_engine.setting.Setting import CorsPolicyMode
from voicevox_engine.setting.SettingLoader import SettingHandler
from voicevox_engine.tts_pipeline.tts_engine import TTSEngineManager
from voicevox_engine.user_dict.user_dict import UserDictionary
from voicevox_engine.utility.path_utility import engine_root, get_save_dir


def generate_app(
    tts_engines: TTSEngineManager,
    core_manager: CoreManager,
    latest_core_version: str,
    setting_loader: SettingHandler,
    preset_manager: PresetManager,
    user_dict: UserDictionary,
    engine_manifest: EngineManifest,
    cancellable_engine: CancellableEngine | None = None,
    root_dir: Path | None = None,
    cors_policy_mode: CorsPolicyMode = CorsPolicyMode.localapps,
    allow_origin: list[str] | None = None,
    disable_mutable_api: bool = False,
) -> FastAPI:
    """ASGI 'application' 仕様に準拠した VOICEVOX ENGINE アプリケーションインスタンスを生成する。"""
    if root_dir is None:
        root_dir = engine_root()

    app = FastAPI(
        title=engine_manifest.name,
        description=f"{engine_manifest.brand_name} の音声合成エンジンです。",
        version=__version__,
    )
    app = configure_middlewares(app, cors_policy_mode, allow_origin)

    if disable_mutable_api:
        deprecated_mutable_api.enable = False

    library_manager = LibraryManager(
        get_save_dir() / "installed_libraries",
        engine_manifest.supported_vvlib_manifest_version,
        engine_manifest.brand_name,
        engine_manifest.name,
        engine_manifest.uuid,
    )

    metas_store = MetasStore(root_dir / "speaker_info")

    app.include_router(
        generate_tts_pipeline_router(
            tts_engines, core_manager, preset_manager, cancellable_engine
        )
    )
    app.include_router(generate_morphing_router(tts_engines, core_manager, metas_store))
    app.include_router(generate_preset_router(preset_manager))
    app.include_router(generate_speaker_router(core_manager, metas_store, root_dir))
    if engine_manifest.supported_features.manage_library:
        app.include_router(generate_library_router(engine_manifest, library_manager))
    app.include_router(generate_user_dict_router(user_dict))
    app.include_router(generate_engine_info_router(core_manager, engine_manifest))
    app.include_router(generate_setting_router(setting_loader, engine_manifest))
    app.include_router(generate_portal_page_router(engine_manifest))

    app = configure_openapi_schema(app)

    return app
