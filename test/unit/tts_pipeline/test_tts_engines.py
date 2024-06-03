""" `TTSEngineManager` クラスのテスト"""

import pytest
from fastapi import HTTPException

from voicevox_engine.dev.tts_engine.mock import MockTTSEngine
from voicevox_engine.tts_pipeline.tts_engine import TTSEngineManager


def test_tts_engines_register_engine() -> None:
    """TTSEngineManager.register_engine() で TTS エンジンを登録できる。"""
    # Inputs
    tts_engines = TTSEngineManager()

    # Test
    tts_engines.register_engine(MockTTSEngine(), "0.0.1")


def test_tts_engines_versions() -> None:
    """TTSEngineManager.versions() でバージョン一覧を取得できる。"""
    # Inputs
    tts_engines = TTSEngineManager()
    tts_engines.register_engine(MockTTSEngine(), "0.0.1")
    tts_engines.register_engine(MockTTSEngine(), "0.0.2")
    # Expects
    true_versions = ["0.0.1", "0.0.2"]
    # Outputs
    versions = tts_engines.versions()

    # Test
    assert true_versions == versions


def test_tts_engines_get_engine_existing() -> None:
    """TTSEngineManager.get_engine() で登録済み TTS エンジンを取得できる。"""
    # Inputs
    tts_engines = TTSEngineManager()
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


def test_tts_engines_get_engine_missing() -> None:
    """TTSEngineManager.get_engine() で存在しない TTS エンジンを取得しようとするとエラーになる。"""
    # Inputs
    tts_engines = TTSEngineManager()
    tts_engine1 = MockTTSEngine()
    tts_engine2 = MockTTSEngine()
    tts_engines.register_engine(tts_engine1, "0.0.1")
    tts_engines.register_engine(tts_engine2, "0.0.2")

    # Test
    with pytest.raises(HTTPException) as _:
        tts_engines.get_engine("0.0.3")


def test_tts_engines_has_engine_true() -> None:
    """TTSEngineManager.has_engine() で TTS エンジンが登録されていることを確認できる。"""
    # Inputs
    tts_engines = TTSEngineManager()
    tts_engines.register_engine(MockTTSEngine(), "0.0.1")
    tts_engines.register_engine(MockTTSEngine(), "0.0.2")
    # Expects
    expected_has = True
    # Outputs
    has = tts_engines.has_engine("0.0.1")

    # Test
    assert expected_has == has


def test_tts_engines_has_engine_false() -> None:
    """TTSEngineManager.has_engine() で TTS エンジンが登録されていないことを確認できる。"""
    # Inputs
    tts_engines = TTSEngineManager()
    tts_engines.register_engine(MockTTSEngine(), "0.0.1")
    tts_engines.register_engine(MockTTSEngine(), "0.0.2")
    # Expects
    expected_has = False
    # Outputs
    has = tts_engines.has_engine("0.0.3")

    # Test
    assert expected_has == has
