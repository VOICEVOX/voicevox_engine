"""VOICEVOX ENGINE へアクセス可能なクライアントの生成"""

import warnings
from pathlib import Path
from typing import Literal

import httpx
from fastapi.testclient import TestClient

from voicevox_engine.app.application import generate_app
from voicevox_engine.core.core_initializer import initialize_cores
from voicevox_engine.preset.PresetManager import PresetManager
from voicevox_engine.setting.SettingLoader import SettingHandler
from voicevox_engine.tts_pipeline.tts_engine import make_tts_engines_from_cores
from voicevox_engine.user_dict.user_dict import UserDictionary
from voicevox_engine.utility.core_version_utility import get_latest_version


def _generate_engine_fake_server(root_dir: Path) -> TestClient:
    cores = initialize_cores(voicevox_dir=root_dir, use_gpu=False, enable_mock=False)
    tts_engines = make_tts_engines_from_cores(cores)
    latest_core_version = get_latest_version(list(tts_engines.keys()))
    setting_loader = SettingHandler(Path("./not_exist.yaml"))
    preset_manager = PresetManager(Path("./presets.yaml"))
    user_dict = UserDictionary()

    app = generate_app(
        tts_engines=tts_engines,
        cores=cores,
        latest_core_version=latest_core_version,
        setting_loader=setting_loader,
        preset_manager=preset_manager,
        root_dir=root_dir,
        user_dict=user_dict,
    )
    return TestClient(app)


# `localhost`: 別プロセスに建てられたローカルの実サーバー
# `fake`: ネットワークを介さずレスポンスを返す疑似サーバー
ServerType = Literal["localhost", "fake"]


def generate_client(
    server: ServerType, root_dir: Path | None
) -> TestClient | httpx.Client:
    """VOICEVOX ENGINE へアクセス可能なクライアントを生成する。"""

    # 前提条件として、製品版 VOICEVOX の archive 版をレポジトリ直下で解凍する必要がある
    if server == "fake":
        if root_dir is None:
            warn_msg = "暗示的に `VOICEVOX/vv-engine` を `root_dir` に設定します。"
            warnings.warn(warn_msg, stacklevel=2)
            root_dir = Path("VOICEVOX/vv-engine")
        return _generate_engine_fake_server(root_dir)
    elif server == "localhost":
        return httpx.Client(base_url="http://localhost:50021")
    else:
        raise Exception(f"{server} はサポートされていないサーバータイプです")
