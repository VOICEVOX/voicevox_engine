from fastapi.testclient import TestClient
from run import generate_app

from voicevox_engine.setting import SettingLoader
from voicevox_engine.synthesis_engine import make_synthesis_engines
from voicevox_engine.utility.core_version_utility import get_latest_core_version

synthesis_engines = make_synthesis_engines(use_gpu=False)
latest_core_version = get_latest_core_version(versions=synthesis_engines.keys())
setting_loader = SettingLoader("./e2e_test_setting.yml")

client = TestClient(
    generate_app(
        synthesis_engines=synthesis_engines,
        latest_core_version=latest_core_version,
        setting_loader=setting_loader,
    )
)
