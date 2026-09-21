"""CPU実行設定の解決と適用"""

import os
import sys
import warnings
from pathlib import Path


def _warn_affinity_unavailable(reason: str) -> None:
    warnings.warn(f"{reason}。CPU affinityは変更しません。", stacklevel=2)


def _select_linux_cpus() -> set[int] | None:
    cpu_directory = Path("/sys/devices/system/cpu")
    try:
        online_cpu_ranges = (cpu_directory / "online").read_text().strip().split(",")
        online_cpus: set[int] = set()
        for cpu_range in online_cpu_ranges:
            if "-" in cpu_range:
                first_cpu, last_cpu = cpu_range.split("-")
                online_cpus.update(range(int(first_cpu), int(last_cpu) + 1))
            else:
                online_cpus.add(int(cpu_range))

        capacities = {
            cpu: int((cpu_directory / f"cpu{cpu}" / "cpu_capacity").read_text())
            for cpu in online_cpus
        }
    except FileNotFoundError:
        _warn_affinity_unavailable("LinuxのCPU capacityを取得できません")
        return None

    highest_capacity = max(capacities.values())
    return {
        cpu for cpu, capacity in capacities.items() if capacity * 2 >= highest_capacity
    }


def _resolve_cpu_num_threads(cpu_num_threads: int | None) -> int:
    if cpu_num_threads is not None and cpu_num_threads != 0:
        return cpu_num_threads

    logical_cpu_count = os.cpu_count()
    if logical_cpu_count is None:
        _warn_affinity_unavailable("CPUスレッド数を決定できません")
        return 0
    return (logical_cpu_count + 1) // 2


def configure_cpu_execution(cpu_num_threads: int | None) -> int:
    """未指定または0なら論理CPU数の半分を切り上げ、条件に合えば高性能CPUへaffinityを設定する。"""
    resolved_cpu_num_threads = _resolve_cpu_num_threads(cpu_num_threads)
    if resolved_cpu_num_threads == 0:
        return resolved_cpu_num_threads

    if sys.platform == "linux":
        candidate_cpus = _select_linux_cpus()
        if candidate_cpus is not None:
            available_cpus = os.sched_getaffinity(0)
            selected_linux_cpus = candidate_cpus & available_cpus
            if (
                selected_linux_cpus != available_cpus
                and len(selected_linux_cpus) > resolved_cpu_num_threads
            ):
                os.sched_setaffinity(0, selected_linux_cpus)
    elif sys.platform == "win32":
        # NOTE: pyhwlocはWindowsだけで使用し、Linux/macOSには入らないため、Windows処理に入ってから読み込む。
        from pyhwloc.topology import CpuBindFlags, Topology

        topology = Topology.from_this_system()
        # NOTE: x86検出はWindowsの初期affinityを変更しうるため無効にする。
        topology.set_components("x86")

        with topology:
            support = topology.get_support().cpubind
            if not (support.get_thisproc_cpubind and support.set_thisproc_cpubind):
                _warn_affinity_unavailable("WindowsでCPU affinityを設定できません")
                return resolved_cpu_num_threads

            flags = CpuBindFlags.PROCESS
            available_cpus = set(topology.get_cpubind(flags))
            kinds = topology.get_cpukinds()
            kind_count = kinds.n_kinds()
            if kind_count == 0:
                _warn_affinity_unavailable("WindowsのCPU性能クラスを取得できません")
                return resolved_cpu_num_threads
            cpuset, efficiency, _ = kinds.get_info(kind_count - 1)
            if efficiency < 0:
                _warn_affinity_unavailable("WindowsのCPU性能クラスを取得できません")
                return resolved_cpu_num_threads
            selected_cpus = set(cpuset) & available_cpus

            if (
                selected_cpus != available_cpus
                and len(selected_cpus) > resolved_cpu_num_threads
            ):
                topology.set_cpubind(selected_cpus, flags)

    return resolved_cpu_num_threads
