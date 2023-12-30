from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from run import generate_app
from syrupy.assertion import SnapshotAssertion
from syrupy.extensions.json import JSONSnapshotExtension

from voicevox_engine.preset import PresetManager
from voicevox_engine.setting import SettingLoader
from voicevox_engine.tts_pipeline import make_cores, make_tts_engines_from_cores
from voicevox_engine.utility.core_version_utility import get_latest_core_version


@pytest.fixture
def snapshot_json(snapshot: SnapshotAssertion):
    """
    syrupyでJSONをsnapshotするためのfixture。

    Examples
    --------
    >>> def test_foo(snapshot_json: JSONSnapshotExtension):
    >>>     assert snapshot_json == {"key": "value"}
    """
    return snapshot.use_extension(JSONSnapshotExtension)


@pytest.fixture(scope="session")
def app_params():
    cores = make_cores(use_gpu=False)
    tts_engines = make_tts_engines_from_cores(cores)
    latest_core_version = get_latest_core_version(
        versions=list(tts_engines.keys())
    )
    setting_loader = SettingLoader(Path("./not_exist.yaml"))
    preset_manager = PresetManager(  # FIXME: impl MockPresetManager
        preset_path=Path("./presets.yaml"),
    )
    return {
        "tts_engines": tts_engines,
        "cores": cores,
        "latest_core_version": latest_core_version,
        "setting_loader": setting_loader,
        "preset_manager": preset_manager,
    }


@pytest.fixture(scope="session")
def client(app_params: dict) -> TestClient:
    return TestClient(generate_app(**app_params))
