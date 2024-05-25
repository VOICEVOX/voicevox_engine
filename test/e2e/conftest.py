from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from voicevox_engine.app.application import generate_app
from voicevox_engine.core.core_initializer import initialize_cores
from voicevox_engine.preset.PresetManager import PresetManager
from voicevox_engine.setting.Setting import SettingHandler
from voicevox_engine.tts_pipeline.tts_engine import make_tts_engines_from_cores
from voicevox_engine.user_dict.user_dict import UserDictionary


@pytest.fixture()
def app_params(tmp_path: Path) -> dict[str, Any]:
    core_manager = initialize_cores(use_gpu=False, enable_mock=True)
    tts_engines = make_tts_engines_from_cores(core_manager)
    latest_core_version = tts_engines.latest_version()
    setting_loader = SettingHandler(Path("./not_exist.yaml"))
    preset_manager = PresetManager(tmp_path / "presets.yaml")
    user_dict = UserDictionary()

    return {
        "tts_engines": tts_engines,
        "core_manager": core_manager,
        "latest_core_version": latest_core_version,
        "setting_loader": setting_loader,
        "preset_manager": preset_manager,
        "user_dict": user_dict,
    }


@pytest.fixture()
def app(app_params: dict) -> FastAPI:
    return generate_app(**app_params)


@pytest.fixture()
def client(app: FastAPI) -> TestClient:
    return TestClient(app)
