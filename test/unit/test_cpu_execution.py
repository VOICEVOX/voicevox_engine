"""`cpu_execution.py` のテスト"""

import os
import sys
import warnings
from enum import IntFlag
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from voicevox_engine.core import cpu_execution


class _FakeCpuBindFlags(IntFlag):
    PROCESS = 1


def test_configure_cpu_execution_uses_explicit_value() -> None:
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


def test_select_linux_cpus_reads_actual_cpu_indices_and_half_capacity() -> None:
    cpu_directory = Path("/sys/devices/system/cpu")
    files = {
        cpu_directory / "online": "0-1,3,5",
        cpu_directory / "cpu0/cpu_capacity": "1024",
        cpu_directory / "cpu1/cpu_capacity": "512",
        cpu_directory / "cpu3/cpu_capacity": "511",
        cpu_directory / "cpu5/cpu_capacity": "1024",
    }
    with patch.object(Path, "read_text", autospec=True, side_effect=files.__getitem__):
        assert cpu_execution._select_linux_cpus() == {0, 1, 5}


@pytest.mark.parametrize("files", [{}, {"online": "0"}])
def test_select_linux_cpus_warns_when_capacity_is_unavailable(
    files: dict[str, str],
) -> None:
    cpu_directory = Path("/sys/devices/system/cpu")
    paths = {
        cpu_directory / "online": files.get("online"),
        cpu_directory / "cpu0/cpu_capacity": files.get("cpu0"),
    }

    def read_text(path: Path) -> str:
        value = paths[path]
        if value is None:
            raise FileNotFoundError(path)
        return value

    with patch.object(Path, "read_text", autospec=True, side_effect=read_text):
        with pytest.warns(UserWarning, match="CPU capacityを取得できません"):
            assert cpu_execution._select_linux_cpus() is None


def test_select_linux_cpus_propagates_permission_error() -> None:
    with patch.object(Path, "read_text", side_effect=PermissionError("読み取れません")):
        with pytest.raises(PermissionError, match="読み取れません"):
            cpu_execution._select_linux_cpus()


def _fake_topology(
    kinds: list[tuple[set[int], int]], available_cpus: set[int]
) -> MagicMock:
    topology = MagicMock()
    topology.get_cpubind.return_value = available_cpus
    topology.get_cpukinds.return_value.n_kinds.return_value = len(kinds)
    topology.get_cpukinds.return_value.get_info.side_effect = lambda index: (
        *kinds[index],
        {},
    )
    topology.get_support.return_value.cpubind = SimpleNamespace(
        get_thisproc_cpubind=True,
        set_thisproc_cpubind=True,
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


@pytest.mark.parametrize(
    ("num_threads", "available_cpus", "should_bind"),
    [(1, {0, 1, 2}, True), (2, {0, 1, 2}, False), (1, {0, 1}, False)],
)
def test_configure_linux_cpu_execution_respects_global_capacity_and_initial_mask(
    num_threads: int, available_cpus: set[int], should_bind: bool
) -> None:
    cpu_directory = Path("/sys/devices/system/cpu")
    files = {
        cpu_directory / "online": "0-2,4",
        cpu_directory / "cpu0/cpu_capacity": "512",
        cpu_directory / "cpu1/cpu_capacity": "512",
        cpu_directory / "cpu2/cpu_capacity": "256",
        cpu_directory / "cpu4/cpu_capacity": "1024",
    }
    with patch.object(Path, "read_text", autospec=True, side_effect=files.__getitem__):
        with patch.object(
            os, "sched_getaffinity", return_value=available_cpus, create=True
        ) as get:
            with patch.object(os, "sched_setaffinity", create=True) as set_affinity:
                with patch.object(sys, "platform", "linux"):
                    with patch.dict(
                        sys.modules, {"pyhwloc": None, "pyhwloc.topology": None}
                    ):
                        assert (
                            cpu_execution.configure_cpu_execution(num_threads)
                            == num_threads
                        )

    get.assert_called_once_with(0)
    if should_bind:
        set_affinity.assert_called_once_with(0, {0, 1})
    else:
        set_affinity.assert_not_called()


def test_configure_linux_cpu_execution_skips_unavailable_capacity() -> None:
    with patch.object(Path, "read_text", side_effect=FileNotFoundError):
        with patch.object(os, "sched_getaffinity", create=True) as get_affinity:
            with patch.object(os, "sched_setaffinity", create=True) as set_affinity:
                with patch.object(sys, "platform", "linux"):
                    with pytest.warns(
                        UserWarning, match="CPU capacityを取得できません"
                    ):
                        assert cpu_execution.configure_cpu_execution(1) == 1

    get_affinity.assert_not_called()
    set_affinity.assert_not_called()


@pytest.mark.parametrize(("num_threads", "should_bind"), [(1, True), (2, False)])
def test_configure_windows_cpu_execution_binds_with_initial_mask(
    num_threads: int, should_bind: bool
) -> None:
    topology = _fake_topology([({2, 3}, 0), ({0, 1, 4}, 1)], {0, 1, 2, 3})
    with patch.dict(sys.modules, _fake_pyhwloc_modules(topology)):
        with patch.object(sys, "platform", "win32"):
            assert cpu_execution.configure_cpu_execution(num_threads) == num_threads

    topology.set_components.assert_called_once_with("x86")
    if should_bind:
        topology.set_cpubind.assert_called_once_with({0, 1}, _FakeCpuBindFlags.PROCESS)
    else:
        topology.set_cpubind.assert_not_called()


def test_configure_windows_cpu_execution_does_not_choose_lower_kind() -> None:
    topology = _fake_topology([({3}, 0), ({0, 1}, 1), ({2}, 2)], {0, 1, 3})
    with patch.dict(sys.modules, _fake_pyhwloc_modules(topology)):
        with patch.object(sys, "platform", "win32"):
            assert cpu_execution.configure_cpu_execution(1) == 1

    topology.set_cpubind.assert_not_called()


def test_configure_windows_cpu_execution_warns_when_binding_is_unsupported() -> None:
    topology = _fake_topology([], {0, 1})
    topology.get_support.return_value.cpubind.get_thisproc_cpubind = False
    topology.get_support.return_value.cpubind.set_thisproc_cpubind = False
    with patch.dict(sys.modules, _fake_pyhwloc_modules(topology)):
        with patch.object(sys, "platform", "win32"):
            with pytest.warns(UserWarning, match="CPU affinityを設定できません"):
                assert cpu_execution.configure_cpu_execution(1) == 1

    topology.set_cpubind.assert_not_called()
