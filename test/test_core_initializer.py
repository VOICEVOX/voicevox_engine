""" `core_initializer.py` のテスト"""

from unittest import TestCase
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from voicevox_engine.core.core_adapter import CoreAdapter
from voicevox_engine.core.core_initializer import CoreManager, get_half_logical_cores
from voicevox_engine.dev.core.mock import MockCoreWrapper


def test_cores_register_core() -> None:
    """CoreManager.register_core() でコアを登録できる。"""
    # Inputs
    cores = CoreManager()

    # Test
    cores.register_core(CoreAdapter(MockCoreWrapper()), "0.0.1")


def test_cores_versions() -> None:
    """CoreManager.versions() でバージョン一覧を取得できる。"""
    # Inputs
    cores = CoreManager()
    cores.register_core(CoreAdapter(MockCoreWrapper()), "0.0.1")
    cores.register_core(CoreAdapter(MockCoreWrapper()), "0.0.2")
    # Expects
    true_versions = ["0.0.1", "0.0.2"]
    # Outputs
    versions = cores.versions()

    # Test
    assert true_versions == versions


def test_cores_latest_version() -> None:
    """CoreManager.latest_version() で最新バージョンを取得できる。"""
    # Inputs
    cores = CoreManager()
    cores.register_core(CoreAdapter(MockCoreWrapper()), "0.0.1")
    cores.register_core(CoreAdapter(MockCoreWrapper()), "0.0.2")
    # Expects
    true_latest_version = "0.0.2"
    # Outputs
    latest_version = cores.latest_version()

    # Test
    assert true_latest_version == latest_version


def test_cores_get_core_specified() -> None:
    """CoreManager.get_core() で登録済みコアをバージョン指定して取得できる。"""
    # Inputs
    cores = CoreManager()
    core1 = CoreAdapter(MockCoreWrapper())
    core2 = CoreAdapter(MockCoreWrapper())
    cores.register_core(core1, "0.0.1")
    cores.register_core(core2, "0.0.2")
    # Expects
    true_acquired_core = core2
    # Outputs
    acquired_core = cores.get_core("0.0.2")

    # Test
    assert true_acquired_core == acquired_core


def test_cores_get_core_latest() -> None:
    """CoreManager.get_core() で最新版コアをバージョン未指定で取得できる。"""
    # Inputs
    cores = CoreManager()
    core1 = CoreAdapter(MockCoreWrapper())
    core2 = CoreAdapter(MockCoreWrapper())
    cores.register_core(core1, "0.0.1")
    cores.register_core(core2, "0.0.2")
    # Expects
    true_acquired_core = core2
    # Outputs
    acquired_core = cores.get_core()

    # Test
    assert true_acquired_core == acquired_core


def test_cores_get_core_missing() -> None:
    """CoreManager.get_core() で存在しないコアを取得しようとするとエラーになる。"""
    # Inputs
    cores = CoreManager()
    core1 = CoreAdapter(MockCoreWrapper())
    core2 = CoreAdapter(MockCoreWrapper())
    cores.register_core(core1, "0.0.1")
    cores.register_core(core2, "0.0.2")

    # Test
    with pytest.raises(HTTPException) as _:
        cores.get_core("0.0.3")


def test_cores_has_core_true() -> None:
    """CoreManager.has_core() でコアが登録されていることを確認できる。"""
    # Inputs
    cores = CoreManager()
    cores.register_core(CoreAdapter(MockCoreWrapper()), "0.0.1")
    cores.register_core(CoreAdapter(MockCoreWrapper()), "0.0.2")
    # Expects
    true_has = True
    # Outputs
    has = cores.has_core("0.0.1")

    # Test
    assert true_has == has


def test_cores_has_core_false() -> None:
    """CoreManager.has_core() でコアが登録されていないことを確認できる。"""
    # Inputs
    cores = CoreManager()
    cores.register_core(CoreAdapter(MockCoreWrapper()), "0.0.1")
    cores.register_core(CoreAdapter(MockCoreWrapper()), "0.0.2")
    # Expects
    true_has = False
    # Outputs
    has = cores.has_core("0.0.3")

    # Test
    assert true_has == has


def test_cores_items() -> None:
    """CoreManager.items() でコアとバージョンのリストを取得できる。"""
    # Inputs
    cores = CoreManager()
    core1 = CoreAdapter(MockCoreWrapper())
    core2 = CoreAdapter(MockCoreWrapper())
    cores.register_core(core1, "0.0.1")
    cores.register_core(core2, "0.0.2")
    # Expects
    true_items = [("0.0.1", core1), ("0.0.2", core2)]
    # Outputs
    items = cores.items()

    # Test
    assert true_items == items


class TestHalfLogicalCores(TestCase):
    @patch("os.cpu_count", return_value=8)
    def test_half_logical_cores_even(self, mock_cpu_count: int) -> None:
        self.assertEqual(get_half_logical_cores(), 4)

    @patch("os.cpu_count", return_value=9)
    def test_half_logical_cores_odd(self, mock_cpu_count: int) -> None:
        self.assertEqual(get_half_logical_cores(), 4)

    @patch("os.cpu_count", return_value=None)
    def test_half_logical_cores_none(self, mock_cpu_count: int) -> None:
        self.assertEqual(get_half_logical_cores(), 0)
