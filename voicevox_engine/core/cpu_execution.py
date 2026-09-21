"""CPU実行設定の解決と適用"""

import os
import platform
import warnings
from typing import cast

import psutil

type _CpuKind = tuple[set[int], int, dict[str, str]]


def _warn_affinity_unavailable(reason: str) -> None:
    warnings.warn(f"{reason}。CPU affinityは変更しません。", stacklevel=1)


def _select_windows_cpus(
    cpu_kinds: list[_CpuKind], available_cpus: set[int]
) -> set[int] | None:
    classes = [
        (cpus & available_cpus, efficiency)
        for cpus, efficiency, _ in cpu_kinds
        if len(cpus & available_cpus) > 0
    ]
    covered_cpus = set().union(*(cpus for cpus, _ in classes))
    if covered_cpus != available_cpus or any(
        efficiency < 0 for _, efficiency in classes
    ):
        _warn_affinity_unavailable("WindowsのCPU性能クラスを取得できません")
        return None

    highest_efficiency = max(efficiency for _, efficiency in classes)
    return set().union(
        *(cpus for cpus, efficiency in classes if efficiency == highest_efficiency)
    )


def _select_linux_cpus(
    cpu_kinds: list[_CpuKind], available_cpus: set[int], pu_os_indices: list[int]
) -> set[int] | None:
    if pu_os_indices != list(range(len(pu_os_indices))):
        _warn_affinity_unavailable("LinuxCapacityと論理CPU番号の対応を確認できません")
        return None

    capacities: dict[int, int] = {}
    for cpus, _, info in cpu_kinds:
        matching_cpus = cpus & available_cpus
        if len(matching_cpus) == 0:
            continue
        capacity_text = info.get("LinuxCapacity")
        if capacity_text is None:
            _warn_affinity_unavailable("LinuxCapacityを取得できません")
            return None
        capacity = int(capacity_text)
        if capacity <= 0:
            raise ValueError("LinuxCapacityは正の整数である必要があります。")
        capacities.update({cpu: capacity for cpu in matching_cpus})

    if capacities.keys() != available_cpus:
        _warn_affinity_unavailable("利用可能な全論理CPUのLinuxCapacityを取得できません")
        return None

    highest_capacity = max(capacities.values())
    return {
        cpu for cpu, capacity in capacities.items() if capacity * 2 >= highest_capacity
    }


def _resolve_cpu_num_threads(cpu_num_threads: int | None) -> int:
    if cpu_num_threads is not None:
        if cpu_num_threads != 0:
            if not 1 <= cpu_num_threads <= 65535:
                raise ValueError(
                    "cpu_num_threadsは0、または1以上65535以下で指定してください。"
                )
            return cpu_num_threads

    logical_cpu_count = cast(int | None, psutil.cpu_count(logical=True))
    if logical_cpu_count is None:
        return 0
    return logical_cpu_count // 2


def configure_cpu_execution(cpu_num_threads: int | None) -> int:
    """CPUスレッド数を解決し、必要なら高性能CPUへCPU affinityを設定する。"""
    resolved_cpu_num_threads = _resolve_cpu_num_threads(cpu_num_threads)
    if resolved_cpu_num_threads == 0:
        _warn_affinity_unavailable("CPUスレッド数を決定できません")
        return resolved_cpu_num_threads

    system = platform.system()
    if system not in ("Windows", "Linux"):
        return resolved_cpu_num_threads

    if system == "Windows" and "HWLOC_CPUKINDS_RANKING" in os.environ:
        _warn_affinity_unavailable("WindowsのCPU性能クラスの順位が変更されています")
        return resolved_cpu_num_threads

    from pyhwloc.topology import CpuBindFlags, Topology

    flags = CpuBindFlags.PROCESS if system == "Windows" else CpuBindFlags.THREAD
    topology = Topology.from_this_system()
    if system == "Windows":
        topology.set_components("x86")

    with topology:
        if system == "Windows":
            from pyhwloc.hwloc.windows import get_nr_processor_groups

            processor_groups = get_nr_processor_groups(topology.native_handle)
            if processor_groups == 0:
                raise RuntimeError("Windows Processor Groupを取得できません。")
            if processor_groups > 1:
                _warn_affinity_unavailable("複数のWindows Processor Groupがあります")
                return resolved_cpu_num_threads

        support = topology.get_support().cpubind
        if system == "Windows":
            can_bind = support.get_thisproc_cpubind and support.set_thisproc_cpubind
        else:
            can_bind = support.get_thisthread_cpubind and support.set_thisthread_cpubind
        if not can_bind:
            _warn_affinity_unavailable(f"{system}でCPU affinityを設定できません")
            return resolved_cpu_num_threads

        available_cpus = set(topology.allowed_cpuset) & set(topology.get_cpubind(flags))
        if len(available_cpus) == 0:
            raise RuntimeError("利用可能な論理CPUがありません。")

        kinds = topology.get_cpukinds()
        cpu_kinds: list[_CpuKind] = []
        for index in range(kinds.n_kinds()):
            cpuset, efficiency, info = kinds.get_info(index)
            cpu_kinds.append((set(cpuset), efficiency, info))

        if system == "Windows":
            selected_cpus = _select_windows_cpus(cpu_kinds, available_cpus)
        else:
            pu_os_indices = [pu.os_index for pu in topology.iter_cpus()]
            selected_cpus = _select_linux_cpus(cpu_kinds, available_cpus, pu_os_indices)

        if (
            selected_cpus is not None
            and selected_cpus != available_cpus
            and len(selected_cpus) > resolved_cpu_num_threads
        ):
            topology.set_cpubind(selected_cpus, flags | CpuBindFlags.STRICT)

    return resolved_cpu_num_threads
