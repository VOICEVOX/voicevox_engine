""" `core_initializer.py` のテスト"""

from unittest.mock import patch

import pytest

from voicevox_engine.core.core_adapter import CoreAdapter
from voicevox_engine.core.core_initializer import (
    CoreManager,
    CoreNotFound,
    get_half_logical_cores,
)
from voicevox_engine.dev.core.mock import MockCoreWrapper


def test_cores_register_core() -> None:
    """CoreManager.register_core() でコアを登録できる。"""
    # Inputs
    core_manager = CoreManager()

    # Test
    core_manager.register_core(CoreAdapter(MockCoreWrapper()), "0.0.1")


def test_cores_versions() -> None:
    """CoreManager.versions() でバージョン一覧を取得できる。"""
    # Inputs
    core_manager = CoreManager()
    core_manager.register_core(CoreAdapter(MockCoreWrapper()), "0.0.1")
    core_manager.register_core(CoreAdapter(MockCoreWrapper()), "0.0.2")
    # Expects
    true_versions = ["0.0.1", "0.0.2"]
    # Outputs
    versions = core_manager.versions()

    # Test
    assert true_versions == versions


def test_cores_latest_version() -> None:
    """CoreManager.latest_version() で最新バージョンを取得できる。"""
    # Inputs
    core_manager = CoreManager()
    core_manager.register_core(CoreAdapter(MockCoreWrapper()), "0.0.1")
    core_manager.register_core(CoreAdapter(MockCoreWrapper()), "0.0.2")
    # Expects
    true_latest_version = "0.0.2"
    # Outputs
    latest_version = core_manager.latest_version()

    # Test
    assert true_latest_version == latest_version


def test_cores_get_core_existing() -> None:
    """CoreManager.get_core() で登録済みコアを取得できる。"""
    # Inputs
    core_manager = CoreManager()
    core1 = CoreAdapter(MockCoreWrapper())
    core2 = CoreAdapter(MockCoreWrapper())
    core_manager.register_core(core1, "0.0.1")
    core_manager.register_core(core2, "0.0.2")
    # Expects
    true_acquired_core = core2
    # Outputs
    acquired_core = core_manager.get_core("0.0.2")

    # Test
    assert true_acquired_core == acquired_core


def test_cores_get_core_missing() -> None:
    """CoreManager.get_core() で存在しないコアを取得しようとするとエラーになる。"""
    # Inputs
    core_manager = CoreManager()
    core1 = CoreAdapter(MockCoreWrapper())
    core2 = CoreAdapter(MockCoreWrapper())
    core_manager.register_core(core1, "0.0.1")
    core_manager.register_core(core2, "0.0.2")

    # Test
    with pytest.raises(CoreNotFound):
        core_manager.get_core("0.0.3")


def test_cores_has_core_true() -> None:
    """CoreManager.has_core() でコアが登録されていることを確認できる。"""
    # Inputs
    core_manager = CoreManager()
    core_manager.register_core(CoreAdapter(MockCoreWrapper()), "0.0.1")
    core_manager.register_core(CoreAdapter(MockCoreWrapper()), "0.0.2")
    # Expects
    expected_has = True
    # Outputs
    has = core_manager.has_core("0.0.1")

    # Test
    assert expected_has == has


def test_cores_has_core_false() -> None:
    """CoreManager.has_core() でコアが登録されていないことを確認できる。"""
    # Inputs
    core_manager = CoreManager()
    core_manager.register_core(CoreAdapter(MockCoreWrapper()), "0.0.1")
    core_manager.register_core(CoreAdapter(MockCoreWrapper()), "0.0.2")
    # Expects
    expected_has = False
    # Outputs
    has = core_manager.has_core("0.0.3")

    # Test
    assert expected_has == has


def test_cores_items() -> None:
    """CoreManager.items() でコアとバージョンのリストを取得できる。"""
    # Inputs
    core_manager = CoreManager()
    core1 = CoreAdapter(MockCoreWrapper())
    core2 = CoreAdapter(MockCoreWrapper())
    core_manager.register_core(core1, "0.0.1")
    core_manager.register_core(core2, "0.0.2")
    # Expects
    true_items = [("0.0.1", core1), ("0.0.2", core2)]
    # Outputs
    items = core_manager.items()

    # Test
    assert true_items == items


@patch("os.cpu_count", return_value=8)
def test_half_logical_cores_even(mock_cpu_count: int) -> None:
    assert get_half_logical_cores() == 4


@patch("os.cpu_count", return_value=9)
def test_half_logical_cores_odd(mock_cpu_count: int) -> None:
    assert get_half_logical_cores() == 4


@patch("os.cpu_count", return_value=None)
def test_half_logical_cores_none(mock_cpu_count: int) -> None:
    assert get_half_logical_cores() == 0
