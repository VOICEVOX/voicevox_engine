from pathlib import Path
from typing import Any

import pytest
import yaml
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

    # テスト用に隔離されたプリセットを生成する
    preset_path = tmp_path / "presets.yaml"
    _generate_preset(preset_path)
    preset_manager = PresetManager(preset_path)

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


def _generate_preset(preset_path: Path) -> None:
    """指定パス下にプリセットファイルを生成する。"""
    contents = [
        {
            "id": 1,
            "name": "サンプルプリセット",
            "speaker_uuid": "7ffcb7ce-00ec-4bdc-82cd-45a8889e43ff",
            "style_id": 0,
            "speedScale": 1,
            "pitchScale": 0,
            "intonationScale": 1,
            "volumeScale": 1,
            "prePhonemeLength": 0.1,
            "postPhonemeLength": 0.1,
        }
    ]
    with open(preset_path, mode="w", encoding="utf-8") as f:
        yaml.safe_dump(contents, f, allow_unicode=True, sort_keys=False)
