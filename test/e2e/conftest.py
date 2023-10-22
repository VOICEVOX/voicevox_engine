from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from run import generate_app

from voicevox_engine.preset import PresetManager
from voicevox_engine.setting import SettingLoader
from voicevox_engine.synthesis_engine import make_synthesis_engines
from voicevox_engine.utility.core_version_utility import get_latest_core_version


@pytest.fixture(scope="session")
def client():
    synthesis_engines = make_synthesis_engines(use_gpu=False)
    latest_core_version = get_latest_core_version(versions=synthesis_engines.keys())
    setting_loader = SettingLoader(Path("./default_setting.yml"))
    preset_manager = PresetManager(  # FIXME: impl MockPresetManager
        preset_path=Path("./presets.yaml"),
    )

    return TestClient(
        generate_app(
            synthesis_engines=synthesis_engines,
            latest_core_version=latest_core_version,
            setting_loader=setting_loader,
            preset_manager=preset_manager,
        )
    )
