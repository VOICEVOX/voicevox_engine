""" `TTSEngines` クラスのテスト"""

import pytest
from fastapi import HTTPException

from voicevox_engine.dev.tts_engine.mock import MockTTSEngine
from voicevox_engine.tts_pipeline.tts_engine import TTSEngines


def test_tts_engines_register_engine() -> None:
    """TTSEngines.register_engine() で TTS エンジンを登録できる。"""
    # Inputs
    tts_engines = TTSEngines()

    # Test
    tts_engines.register_engine(MockTTSEngine(), "0.0.1")


def test_tts_engines_versions() -> None:
    """TTSEngines.versions でバージョン一覧を取得できる。"""
    # Inputs
    tts_engines = TTSEngines()
    tts_engines.register_engine(MockTTSEngine(), "0.0.1")
    tts_engines.register_engine(MockTTSEngine(), "0.0.2")
    # Expects
    true_versions = ["0.0.1", "0.0.2"]
    # Outputs
    versions = tts_engines.versions

    # Test
    assert true_versions == versions


def test_tts_engines_latest_version() -> None:
    """TTSEngines.latest_version で最新バージョンを取得できる。"""
    # Inputs
    tts_engines = TTSEngines()
    tts_engines.register_engine(MockTTSEngine(), "0.0.1")
    tts_engines.register_engine(MockTTSEngine(), "0.0.2")
    # Expects
    true_latest_version = "0.0.2"
    # Outputs
    latest_version = tts_engines.latest_version

    # Test
    assert true_latest_version == latest_version


def test_tts_engines_get_engine_specified() -> None:
    """TTSEngines.get_engine() で登録済み TTS エンジンをバージョン指定して取得できる。"""
    # Inputs
    tts_engines = TTSEngines()
    tts_engine1 = MockTTSEngine()
    tts_engine2 = MockTTSEngine()
    tts_engines.register_engine(tts_engine1, "0.0.1")
    tts_engines.register_engine(tts_engine2, "0.0.2")
    # Expects
    true_acquired_tts_engine = tts_engine2
    # Outputs
    acquired_tts_engine = tts_engines.get_engine("0.0.2")

    # Test
    assert true_acquired_tts_engine == acquired_tts_engine


def test_tts_engines_get_engine_latest() -> None:
    """TTSEngines.get_engine() で最新版 TTS エンジンをバージョン未指定で取得できる。"""
    # Inputs
    tts_engines = TTSEngines()
    tts_engine1 = MockTTSEngine()
    tts_engine2 = MockTTSEngine()
    tts_engines.register_engine(tts_engine1, "0.0.1")
    tts_engines.register_engine(tts_engine2, "0.0.2")
    # Expects
    true_acquired_tts_engine = tts_engine2
    # Outputs
    acquired_tts_engine = tts_engines.get_engine()

    # Test
    assert true_acquired_tts_engine == acquired_tts_engine


def test_tts_engines_get_engine_missing() -> None:
    """TTSEngines.get_engine() で存在しない TTS エンジンを取得しようとするとエラーになる。"""
    # Inputs
    tts_engines = TTSEngines()
    tts_engine1 = MockTTSEngine()
    tts_engine2 = MockTTSEngine()
    tts_engines.register_engine(tts_engine1, "0.0.1")
    tts_engines.register_engine(tts_engine2, "0.0.2")

    # Test
    with pytest.raises(HTTPException) as _:
        tts_engines.get_engine("0.0.3")


def test_tts_engines_has_engine_true() -> None:
    """TTSEngines.has_engine() で TTS エンジンが登録されていることを確認できる。"""
    # Inputs
    tts_engines = TTSEngines()
    tts_engines.register_engine(MockTTSEngine(), "0.0.1")
    tts_engines.register_engine(MockTTSEngine(), "0.0.2")
    # Expects
    true_has = True
    # Outputs
    has = tts_engines.has_engine("0.0.1")

    # Test
    assert true_has == has


def test_tts_engines_has_engine_false() -> None:
    """TTSEngines.has_engine() で TTS エンジンが登録されていないことを確認できる。"""
    # Inputs
    tts_engines = TTSEngines()
    tts_engines.register_engine(MockTTSEngine(), "0.0.1")
    tts_engines.register_engine(MockTTSEngine(), "0.0.2")
    # Expects
    true_has = False
    # Outputs
    has = tts_engines.has_engine("0.0.3")

    # Test
    assert true_has == has
