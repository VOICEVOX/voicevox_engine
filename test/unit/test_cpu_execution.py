"""`cpu_execution.py` のテスト"""

import os
import platform
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


@pytest.mark.parametrize("cpu_num_threads", [1, 65535])
def test_configure_cpu_execution_uses_explicit_value(cpu_num_threads: int) -> None:
    with patch.object(platform, "system", return_value="Darwin"):
        assert cpu_execution.configure_cpu_execution(cpu_num_threads) == cpu_num_threads


@pytest.mark.parametrize("cpu_num_threads", [None, 0])
@pytest.mark.parametrize(
    ("logical_cpu_count", "expected"),
    [(1, 1), (2, 1), (3, 2), (4, 2), (5, 3), (9, 5)],
)
def test_configure_cpu_execution_resolves_automatic_value(
    cpu_num_threads: int | None, logical_cpu_count: int, expected: int
) -> None:
    with patch.object(platform, "system", return_value="Darwin"):
        with patch.object(os, "cpu_count", return_value=logical_cpu_count):
            assert cpu_execution.configure_cpu_execution(cpu_num_threads) == expected


def test_configure_cpu_execution_warns_when_cpu_count_is_unknown() -> None:
    with patch.object(os, "cpu_count", return_value=None):
        with pytest.warns(UserWarning, match="CPUスレッド数を決定できません"):
            assert cpu_execution.configure_cpu_execution(None) == 0


def test_configure_cpu_execution_does_not_warn_for_one_logical_cpu() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        with patch.object(os, "cpu_count", return_value=1):
            with patch.object(platform, "system", return_value="Darwin"):
                assert cpu_execution.configure_cpu_execution(None) == 1


def test_select_windows_cpus_uses_highest_class_with_initial_mask() -> None:
    kinds: list[cpu_execution._CpuKind] = [
        ({2, 3}, 0, {}),
        ({0, 1, 4}, 1, {}),
    ]
    assert cpu_execution._select_windows_cpus(kinds, {0, 1, 2, 3}) == {0, 1}


def test_select_windows_cpus_warns_when_class_is_missing() -> None:
    kinds: list[cpu_execution._CpuKind] = [({0}, -1, {}), ({1}, -1, {})]
    with pytest.warns(UserWarning, match="CPU性能クラスを取得できません"):
        assert cpu_execution._select_windows_cpus(kinds, {0, 1}) is None


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


@pytest.mark.parametrize("files", [{}, {"online": "0"}, {"online": "0", "cpu0": "0"}])
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


def _fake_topology(
    kinds: list[cpu_execution._CpuKind], available_cpus: set[int]
) -> MagicMock:
    topology = MagicMock()
    topology.allowed_cpuset = {0}
    topology.get_cpubind.return_value = available_cpus
    topology.get_cpukinds.return_value.n_kinds.return_value = len(kinds)
    topology.get_cpukinds.return_value.get_info.side_effect = kinds
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
def test_configure_linux_cpu_execution_respects_initial_mask(
    num_threads: int, available_cpus: set[int], should_bind: bool
) -> None:
    cpu_directory = Path("/sys/devices/system/cpu")
    files = {
        cpu_directory / "online": "0-2,4",
        cpu_directory / "cpu0/cpu_capacity": "1024",
        cpu_directory / "cpu1/cpu_capacity": "1024",
        cpu_directory / "cpu2/cpu_capacity": "400",
        cpu_directory / "cpu4/cpu_capacity": "2048",
    }
    with patch.object(Path, "read_text", autospec=True, side_effect=files.__getitem__):
        with patch.object(os, "sched_getaffinity", return_value=available_cpus) as get:
            with patch.object(os, "sched_setaffinity") as set_affinity:
                with patch.object(platform, "system", return_value="Linux"):
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


def test_configure_linux_cpu_execution_propagates_binding_failure() -> None:
    with patch.object(cpu_execution, "_select_linux_cpus", return_value={0, 1}):
        with patch.object(os, "sched_getaffinity", return_value={0, 1, 2}):
            with patch.object(os, "sched_setaffinity", side_effect=OSError("失敗")):
                with patch.object(platform, "system", return_value="Linux"):
                    with pytest.raises(OSError, match="失敗"):
                        cpu_execution.configure_cpu_execution(1)


def test_configure_linux_cpu_execution_skips_unavailable_capacity() -> None:
    with patch.object(Path, "read_text", side_effect=FileNotFoundError):
        with patch.object(os, "sched_getaffinity") as get_affinity:
            with patch.object(os, "sched_setaffinity") as set_affinity:
                with patch.object(platform, "system", return_value="Linux"):
                    with pytest.warns(
                        UserWarning, match="CPU capacityを取得できません"
                    ):
                        assert cpu_execution.configure_cpu_execution(1) == 1

    get_affinity.assert_not_called()
    set_affinity.assert_not_called()


def test_configure_windows_cpu_execution_binds_with_initial_mask() -> None:
    kinds: list[cpu_execution._CpuKind] = [({2}, 0, {}), ({0, 1}, 1, {})]
    topology = _fake_topology(kinds, {0, 1, 2})
    with patch.dict(sys.modules, _fake_pyhwloc_modules(topology)):
        with patch.object(platform, "system", return_value="Windows"):
            assert cpu_execution.configure_cpu_execution(1) == 1

    topology.set_components.assert_called_once_with("x86")
    topology.get_cpubind.assert_called_once_with(_FakeCpuBindFlags.PROCESS)
    topology.set_cpubind.assert_called_once_with({0, 1}, _FakeCpuBindFlags.PROCESS)


def test_configure_windows_cpu_execution_warns_when_binding_is_unsupported() -> None:
    topology = _fake_topology([], {0, 1})
    topology.get_support.return_value.cpubind.get_thisproc_cpubind = False
    topology.get_support.return_value.cpubind.set_thisproc_cpubind = False
    with patch.dict(sys.modules, _fake_pyhwloc_modules(topology)):
        with patch.object(platform, "system", return_value="Windows"):
            with pytest.warns(UserWarning, match="CPU affinityを設定できません"):
                assert cpu_execution.configure_cpu_execution(1) == 1

    topology.set_cpubind.assert_not_called()
