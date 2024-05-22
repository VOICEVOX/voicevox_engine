import json
import shutil
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from voicevox_engine.app.application import generate_app
from voicevox_engine.core.core_initializer import initialize_cores
from voicevox_engine.preset.PresetManager import PresetManager
from voicevox_engine.setting.SettingLoader import SettingHandler
from voicevox_engine.tts_pipeline.tts_engine import make_tts_engines_from_cores
from voicevox_engine.user_dict.user_dict import DEFAULT_DICT_PATH, UserDictionary


def copy_under_dir(file_path: Path, dir_path: Path) -> Path:
    """指定ディレクトリ下へファイルをコピーする。"""
    copied_file_path = dir_path / file_path.name
    shutil.copyfile(file_path, copied_file_path)
    return copied_file_path


@pytest.fixture()
def app_params(tmp_path: Path) -> dict[str, Any]:
    cores = initialize_cores(use_gpu=False, enable_mock=True)
    tts_engines = make_tts_engines_from_cores(cores)
    latest_core_version = tts_engines.latest_version()
    setting_loader = SettingHandler(Path("./not_exist.yaml"))

    # 隔離されたプリセットの生成
    preset_path = Path("./presets.yaml")
    preset_manager = PresetManager(copy_under_dir(preset_path, tmp_path))

    # 隔離されたユーザー辞書の生成
    user_dict = UserDictionary(
        default_dict_path=copy_under_dir(DEFAULT_DICT_PATH, tmp_path),
        user_dict_path=generate_user_dict(tmp_path),
        compiled_dict_path=tmp_path / "user.dic",
    )

    return {
        "tts_engines": tts_engines,
        "cores": cores,
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


def generate_user_dict(dir_path: Path) -> Path:
    """指定されたディレクトリ下にユーザー辞書ファイルを生成する。"""
    contents = {
        "a89596ad-caa8-4f4e-8eb3-3d2261c798fd": {
            "surface": "ｔｅｓｔ１",
            "context_id": 1348,
            "part_of_speech": "名詞",
            "part_of_speech_detail_1": "固有名詞",
            "part_of_speech_detail_2": "一般",
            "part_of_speech_detail_3": "*",
            "inflectional_type": "*",
            "inflectional_form": "*",
            "stem": "*",
            "yomi": "テストイチ",
            "pronunciation": "テストイチ",
            "accent_type": 1,
            "mora_count": 3,
            "accent_associative_rule": "*",
            "cost": 8609,
        },
        "c89596ad-caa8-4f4e-8eb3-3d2261c798fd": {
            "surface": "ｔｅｓｔ２",
            "context_id": 1348,
            "part_of_speech": "名詞",
            "part_of_speech_detail_1": "固有名詞",
            "part_of_speech_detail_2": "一般",
            "part_of_speech_detail_3": "*",
            "inflectional_type": "*",
            "inflectional_form": "*",
            "stem": "*",
            "yomi": "テストニ",
            "pronunciation": "テストニ",
            "accent_type": 1,
            "mora_count": 2,
            "accent_associative_rule": "*",
            "cost": 8608,
        },
    }
    contents_json = json.dumps(contents, ensure_ascii=False)

    file_path = dir_path / "user_dict_for_test.json"
    file_path.write_text(contents_json, encoding="utf-8")

    return file_path
