"""`cpu_execution.py` のテスト"""

import os
import platform
import sys
import warnings
from enum import IntFlag
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from voicevox_engine.core import cpu_execution


class _FakeCpuBindFlags(IntFlag):
    PROCESS = 1
    THREAD = 2
    STRICT = 4


@pytest.mark.parametrize("cpu_num_threads", [1, 65535])
def test_configure_cpu_execution_uses_explicit_value(cpu_num_threads: int) -> None:
    with patch.object(platform, "system", return_value="Darwin"):
        assert cpu_execution.configure_cpu_execution(cpu_num_threads) == cpu_num_threads


@pytest.mark.parametrize("cpu_num_threads", [None, 0])
def test_configure_cpu_execution_resolves_automatic_value(
    cpu_num_threads: int | None,
) -> None:
    with patch.object(platform, "system", return_value="Darwin"):
        with patch.object(os, "cpu_count", return_value=9):
            assert cpu_execution.configure_cpu_execution(cpu_num_threads) == 4


@pytest.mark.parametrize("cpu_num_threads", [-1, 65536])
def test_configure_cpu_execution_rejects_invalid_value(cpu_num_threads: int) -> None:
    with pytest.raises(ValueError, match="cpu_num_threads"):
        cpu_execution.configure_cpu_execution(cpu_num_threads)


def test_configure_cpu_execution_warns_when_cpu_count_is_unknown() -> None:
    with patch.object(os, "cpu_count", return_value=None):
        with pytest.warns(UserWarning, match="CPUスレッド数を決定できません"):
            assert cpu_execution.configure_cpu_execution(None) == 0


def test_configure_cpu_execution_does_not_warn_for_one_logical_cpu() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        with patch.object(os, "cpu_count", return_value=1):
            assert cpu_execution.configure_cpu_execution(None) == 0


def test_select_windows_cpus_uses_highest_class_with_initial_mask() -> None:
    kinds: list[cpu_execution._CpuKind] = [
        ({0, 1, 4}, 1, {}),
        ({2, 3}, 0, {}),
    ]
    assert cpu_execution._select_windows_cpus(kinds, {0, 1, 2, 3}) == {0, 1}


def test_select_windows_cpus_warns_when_class_is_missing() -> None:
    kinds: list[cpu_execution._CpuKind] = [({0}, 1, {}), ({1}, -1, {})]
    with pytest.warns(UserWarning, match="CPU性能クラスを取得できません"):
        assert cpu_execution._select_windows_cpus(kinds, {0, 1}) is None


def test_select_linux_cpus_includes_half_capacity_with_initial_mask() -> None:
    kinds: list[cpu_execution._CpuKind] = [
        ({0, 1, 4}, 1, {"LinuxCapacity": "1024"}),
        ({2}, 0, {"LinuxCapacity": "512"}),
        ({3}, 0, {"LinuxCapacity": "511"}),
    ]
    assert cpu_execution._select_linux_cpus(kinds, {0, 1, 2, 3}, [4, 2, 0, 3, 1]) == {
        0,
        1,
        2,
    }


@pytest.mark.parametrize("info", [{}, {"LinuxCapacity": "0"}])
def test_select_linux_cpus_warns_when_capacity_is_missing_or_zero(
    info: dict[str, str],
) -> None:
    with pytest.warns(UserWarning, match="LinuxCapacityを取得できません"):
        assert cpu_execution._select_linux_cpus([({0}, 0, info)], {0}, [0]) is None


def test_select_linux_cpus_rejects_negative_capacity() -> None:
    with pytest.raises(ValueError, match="LinuxCapacity"):
        cpu_execution._select_linux_cpus([({0}, 0, {"LinuxCapacity": "-1"})], {0}, [0])


def test_select_linux_cpus_propagates_invalid_capacity() -> None:
    with pytest.raises(ValueError, match="invalid literal"):
        cpu_execution._select_linux_cpus(
            [({0}, 0, {"LinuxCapacity": "invalid"})], {0}, [0]
        )


@pytest.mark.parametrize(
    ("pu_os_indices", "available_cpus"),
    [([0, 2], {0, 2}), ([0, 0, 1], {0, 1})],
)
def test_select_linux_cpus_warns_when_cpu_indices_have_gaps_or_duplicates(
    pu_os_indices: list[int], available_cpus: set[int]
) -> None:
    with pytest.warns(UserWarning, match="論理CPU番号の対応を確認できません"):
        assert (
            cpu_execution._select_linux_cpus([], available_cpus, pu_os_indices) is None
        )


def _fake_topology(
    kinds: list[cpu_execution._CpuKind], available_cpus: set[int]
) -> MagicMock:
    topology = MagicMock()
    topology.allowed_cpuset = {0, 1, 2, 3, 4}
    topology.get_cpubind.return_value = available_cpus
    topology.get_cpukinds.return_value.n_kinds.return_value = len(kinds)
    topology.get_cpukinds.return_value.get_info.side_effect = kinds
    topology.iter_cpus.return_value = [
        SimpleNamespace(os_index=index) for index in range(5)
    ]
    topology.get_support.return_value.cpubind = SimpleNamespace(
        get_thisproc_cpubind=True,
        set_thisproc_cpubind=True,
        get_thisthread_cpubind=True,
        set_thisthread_cpubind=True,
    )
    return topology


def _fake_pyhwloc_modules(topology: MagicMock) -> dict[str, ModuleType]:
    package = ModuleType("pyhwloc")
    topology_module = ModuleType("pyhwloc.topology")
    topology_module.__dict__["CpuBindFlags"] = _FakeCpuBindFlags
    topology_module.__dict__["Topology"] = SimpleNamespace(
        from_this_system=MagicMock(return_value=topology)
    )
    return {
        "pyhwloc": package,
        "pyhwloc.topology": topology_module,
    }


@pytest.mark.parametrize("num_threads", [1, 2])
def test_configure_linux_cpu_execution_respects_initial_mask(
    num_threads: int,
) -> None:
    kinds: list[cpu_execution._CpuKind] = [
        ({0, 1, 3, 4}, 1, {"LinuxCapacity": "1024"}),
        ({2}, 0, {"LinuxCapacity": "400"}),
    ]
    topology = _fake_topology(kinds, {0, 1, 2})
    with patch.dict(sys.modules, _fake_pyhwloc_modules(topology)):
        with patch.object(platform, "system", return_value="Linux"):
            assert cpu_execution.configure_cpu_execution(num_threads) == num_threads

    if num_threads == 1:
        topology.set_cpubind.assert_called_once_with(
            {0, 1}, _FakeCpuBindFlags.THREAD | _FakeCpuBindFlags.STRICT
        )
    else:
        topology.set_cpubind.assert_not_called()


def test_configure_windows_cpu_execution_binds_with_ranking_variable() -> None:
    kinds: list[cpu_execution._CpuKind] = [({0, 1}, 1, {}), ({2}, 0, {})]
    topology = _fake_topology(kinds, {0, 1, 2})
    with patch.dict(sys.modules, _fake_pyhwloc_modules(topology)):
        with patch.dict(os.environ, {"HWLOC_CPUKINDS_RANKING": "coretype"}):
            with patch.object(platform, "system", return_value="Windows"):
                assert cpu_execution.configure_cpu_execution(1) == 1

    topology.set_components.assert_called_once_with("x86")
    topology.set_cpubind.assert_called_once_with(
        {0, 1}, _FakeCpuBindFlags.PROCESS | _FakeCpuBindFlags.STRICT
    )


@pytest.mark.parametrize(
    ("get_supported", "set_supported"), [(False, True), (True, False)]
)
def test_configure_windows_cpu_execution_warns_when_binding_is_unsupported(
    get_supported: bool, set_supported: bool
) -> None:
    topology = _fake_topology([], {0, 1})
    topology.get_support.return_value.cpubind.get_thisproc_cpubind = get_supported
    topology.get_support.return_value.cpubind.set_thisproc_cpubind = set_supported
    with patch.dict(sys.modules, _fake_pyhwloc_modules(topology)):
        with patch.object(platform, "system", return_value="Windows"):
            with pytest.warns(UserWarning, match="CPU affinityを設定できません"):
                assert cpu_execution.configure_cpu_execution(1) == 1

    topology.set_cpubind.assert_not_called()
