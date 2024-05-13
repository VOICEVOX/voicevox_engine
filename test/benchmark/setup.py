from pathlib import Path

from fastapi.testclient import TestClient

from voicevox_engine.app.application import generate_app
from voicevox_engine.core.core_initializer import initialize_cores
from voicevox_engine.preset.PresetManager import PresetManager
from voicevox_engine.setting.SettingLoader import SettingHandler
from voicevox_engine.tts_pipeline.tts_engine import make_tts_engines_from_cores
from voicevox_engine.utility.core_version_utility import get_latest_version


def generate_engine_fake_server() -> TestClient:
    # 前提条件として、製品版 VOICEVOX の archive 版をレポジトリ直下で解凍する必要がある
    root_dir = Path("VOICEVOX/vv-engine")

    cores = initialize_cores(voicevox_dir=root_dir, use_gpu=False, enable_mock=False)
    tts_engines = make_tts_engines_from_cores(cores)
    latest_core_version = get_latest_version(list(tts_engines.keys()))
    setting_loader = SettingHandler(Path("./not_exist.yaml"))
    preset_manager = PresetManager(Path("./presets.yaml"))

    app = generate_app(
        tts_engines=tts_engines,
        cores=cores,
        latest_core_version=latest_core_version,
        setting_loader=setting_loader,
        preset_manager=preset_manager,
        root_dir=root_dir,
    )
    return TestClient(app)
