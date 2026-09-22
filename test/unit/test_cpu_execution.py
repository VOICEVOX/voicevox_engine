"""`cpu_execution.py` のテスト"""

import os
import sys
import warnings
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock, call, patch

import pytest

from voicevox_engine.core import cpu_execution

_FakeCpuBindFlags = SimpleNamespace(PROCESS=object(), THREAD=object())


_FakeTopologyFlags = SimpleNamespace(INCLUDE_DISALLOWED=object())


def _fake_topology(
    kinds: list[tuple[set[int], int, dict[str, str]]],
    available_cpus: set[int],
    cpuset: set[int],
) -> MagicMock:
    topology = MagicMock()
    topology.get_cpubind.return_value = available_cpus
    topology.cpuset = cpuset
    topology.get_cpukinds.return_value.n_kinds.return_value = len(kinds)
    topology.get_cpukinds.return_value.get_info.side_effect = lambda index: kinds[index]
    topology.get_support.return_value.cpubind = SimpleNamespace(
        get_thisproc_cpubind=True,
        set_thisproc_cpubind=True,
    )
    return topology


def _fake_pyhwloc_modules(topology: MagicMock) -> dict[str, ModuleType]:
    package = ModuleType("pyhwloc")
    topology_module = ModuleType("pyhwloc.topology")
    topology_module.__dict__["CpuBindFlags"] = _FakeCpuBindFlags
    topology_module.__dict__["TopologyFlags"] = _FakeTopologyFlags
    topology_module.__dict__["Topology"] = SimpleNamespace(
        from_this_system=MagicMock(return_value=topology)
    )
    return {
        "pyhwloc": package,
        "pyhwloc.topology": topology_module,
    }


def test_configure_cpu_execution_uses_explicit_value_without_pyhwloc_on_macos() -> None:
    with patch.dict(sys.modules, {"pyhwloc": None, "pyhwloc.topology": None}):
        with patch.object(sys, "platform", "darwin"):
            assert cpu_execution.configure_cpu_execution(1) == 1


@pytest.mark.parametrize("cpu_num_threads", [None, 0])
@pytest.mark.parametrize(
    ("logical_cpu_count", "expected"),
    [(1, 1), (2, 1), (3, 2)],
)
def test_configure_cpu_execution_resolves_automatic_value(
    cpu_num_threads: int | None, logical_cpu_count: int, expected: int
) -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        with patch.object(sys, "platform", "darwin"):
            with patch.object(os, "cpu_count", return_value=logical_cpu_count):
                assert (
                    cpu_execution.configure_cpu_execution(cpu_num_threads) == expected
                )


def test_configure_cpu_execution_warns_when_cpu_count_is_unknown() -> None:
    with patch.object(os, "cpu_count", return_value=None):
        with pytest.warns(UserWarning, match="CPUスレッド数を決定できません"):
            assert cpu_execution.configure_cpu_execution(None) == 0


@pytest.mark.parametrize(
    ("num_threads", "available_cpus", "should_bind", "expected_selected_cpus"),
    [
        (1, {0, 1, 2}, True, {0, 1}),
        (2, {0, 1, 2}, False, {0, 1}),
        (1, {0, 1}, False, {0, 1}),
        (1, {0, 1, 2, 3}, True, {0, 1, 3}),
    ],
)
def test_configure_linux_cpu_execution_respects_global_capacity_and_initial_mask(
    num_threads: int,
    available_cpus: set[int],
    should_bind: bool,
    expected_selected_cpus: set[int],
) -> None:
    topology = _fake_topology(
        [
            ({0, 1}, 0, {"LinuxCapacity": "512"}),
            ({2}, 1, {"LinuxCapacity": "511"}),
            ({3}, 2, {"LinuxCapacity": "1024"}),
        ],
        available_cpus,
        {0, 1, 2, 3},
    )
    with patch.dict(sys.modules, _fake_pyhwloc_modules(topology)):
        with patch.object(sys, "platform", "linux"):
            assert cpu_execution.configure_cpu_execution(num_threads) == num_threads

    topology.set_flags.assert_called_once_with(_FakeTopologyFlags.INCLUDE_DISALLOWED)
    assert topology.mock_calls.index(
        call.set_flags(_FakeTopologyFlags.INCLUDE_DISALLOWED)
    ) < topology.mock_calls.index(call.__enter__())
    topology.get_cpubind.assert_called_once_with(_FakeCpuBindFlags.THREAD)
    if should_bind:
        topology.set_cpubind.assert_called_once_with(
            expected_selected_cpus, _FakeCpuBindFlags.THREAD
        )
    else:
        topology.set_cpubind.assert_not_called()


@pytest.mark.parametrize(
    ("kinds", "cpuset", "warning"),
    [
        ([], {0, 1}, "CPU capacityを取得できません"),
        ([({0, 1}, 0, {})], {0, 1}, "CPU capacityを取得できません"),
        (
            [({0, 2}, 0, {"LinuxCapacity": "1024"})],
            {0, 2},
            "CPU番号に欠番",
        ),
    ],
)
def test_configure_linux_cpu_execution_skips_unavailable_capacity(
    kinds: list[tuple[set[int], int, dict[str, str]]],
    cpuset: set[int],
    warning: str,
) -> None:
    topology = _fake_topology(kinds, cpuset, cpuset)
    with patch.dict(sys.modules, _fake_pyhwloc_modules(topology)):
        with patch.object(sys, "platform", "linux"):
            with pytest.warns(UserWarning, match=warning):
                assert cpu_execution.configure_cpu_execution(1) == 1

    topology.get_cpubind.assert_not_called()
    topology.set_cpubind.assert_not_called()


@pytest.mark.parametrize(("num_threads", "should_bind"), [(1, True), (2, False)])
def test_configure_windows_cpu_execution_binds_with_initial_mask(
    num_threads: int, should_bind: bool
) -> None:
    topology = _fake_topology(
        [({2, 3}, 0, {}), ({0, 1, 4}, 1, {})],
        {0, 1, 2, 3},
        {0, 1, 2, 3, 4},
    )
    with patch.dict(sys.modules, _fake_pyhwloc_modules(topology)):
        with patch.object(sys, "platform", "win32"):
            assert cpu_execution.configure_cpu_execution(num_threads) == num_threads

    topology.set_components.assert_called_once_with("x86")
    topology.get_cpubind.assert_called_once_with(_FakeCpuBindFlags.PROCESS)
    if should_bind:
        topology.set_cpubind.assert_called_once_with({0, 1}, _FakeCpuBindFlags.PROCESS)
    else:
        topology.set_cpubind.assert_not_called()


def test_configure_windows_cpu_execution_does_not_choose_lower_kind() -> None:
    topology = _fake_topology(
        [({3}, 0, {}), ({0, 1}, 1, {}), ({2}, 2, {})],
        {0, 1, 3},
        {0, 1, 2, 3},
    )
    with patch.dict(sys.modules, _fake_pyhwloc_modules(topology)):
        with patch.object(sys, "platform", "win32"):
            assert cpu_execution.configure_cpu_execution(1) == 1

    topology.set_cpubind.assert_not_called()


def test_configure_windows_cpu_execution_warns_when_binding_is_unsupported() -> None:
    topology = _fake_topology([], {0, 1}, {0, 1})
    topology.get_support.return_value.cpubind.get_thisproc_cpubind = False
    topology.get_support.return_value.cpubind.set_thisproc_cpubind = False
    with patch.dict(sys.modules, _fake_pyhwloc_modules(topology)):
        with patch.object(sys, "platform", "win32"):
            with pytest.warns(UserWarning, match="CPU affinityを設定できません"):
                assert cpu_execution.configure_cpu_execution(1) == 1

    topology.set_cpubind.assert_not_called()
