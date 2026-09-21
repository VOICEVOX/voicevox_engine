"""CPU実行設定の解決と適用"""

import os
import platform
import warnings
from pathlib import Path

type _CpuKind = tuple[set[int], int, dict[str, str]]


def _warn_affinity_unavailable(reason: str) -> None:
    warnings.warn(f"{reason}。CPU affinityは変更しません。", stacklevel=2)


def _select_windows_cpus(
    cpu_kinds: list[_CpuKind], available_cpus: set[int]
) -> set[int] | None:
    classes = []
    for cpus, efficiency, _ in cpu_kinds:
        matching_cpus = cpus & available_cpus
        if len(matching_cpus) > 0:
            classes.append((matching_cpus, efficiency))
    covered_cpus = set().union(*(cpus for cpus, _ in classes))
    if covered_cpus != available_cpus or any(
        efficiency < 0 for _, efficiency in classes
    ):
        _warn_affinity_unavailable("WindowsのCPU性能クラスを取得できません")
        return None

    return max(classes, key=lambda item: item[1])[0]


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

        # NOTE: pyhwloc 3.0.1同梱hwlocは列挙番号からcapacityを読み値も補正するため、実CPU番号のsysfs値を使う。
        capacities = {
            cpu: int((cpu_directory / f"cpu{cpu}" / "cpu_capacity").read_text())
            for cpu in online_cpus
        }
    except OSError:
        _warn_affinity_unavailable("LinuxのCPU capacityを取得できません")
        return None

    if any(capacity == 0 for capacity in capacities.values()):
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
    """
    CPUスレッド数を決定し、条件に合えば高性能CPUへCPU affinityを設定する。

    未指定または0の場合は論理CPU数の半分を小数点以下切り上げで使い、論理CPU数を取得できなければ警告して0を返す。
    Windowsでは高いCPU性能クラス、Linuxでは最大のCPU capacityの半分以上を持つ論理CPUを候補とし、既存の許可CPUの範囲で候補数が決定したスレッド数を超える場合にaffinityを設定する。
    """
    resolved_cpu_num_threads = _resolve_cpu_num_threads(cpu_num_threads)
    if resolved_cpu_num_threads == 0:
        return resolved_cpu_num_threads

    system = platform.system()
    if system == "Linux":
        candidate_cpus = _select_linux_cpus()
        if candidate_cpus is not None:
            available_cpus = os.sched_getaffinity(0)
            selected_linux_cpus = candidate_cpus & available_cpus
            if (
                selected_linux_cpus != available_cpus
                and len(selected_linux_cpus) > resolved_cpu_num_threads
            ):
                os.sched_setaffinity(0, selected_linux_cpus)
        return resolved_cpu_num_threads

    if system != "Windows":
        return resolved_cpu_num_threads

    # NOTE: pyhwlocはWindowsだけで使用し、Linux/macOSには入らないため、Windows処理に入ってから読み込む。
    from pyhwloc.topology import CpuBindFlags, Topology

    topology = Topology.from_this_system()
    topology.set_components("x86")

    with topology:
        support = topology.get_support().cpubind
        if not (support.get_thisproc_cpubind and support.set_thisproc_cpubind):
            _warn_affinity_unavailable(f"{system}でCPU affinityを設定できません")
            return resolved_cpu_num_threads

        flags = CpuBindFlags.PROCESS
        available_cpus = set(topology.get_cpubind(flags))
        kinds = topology.get_cpukinds()
        cpu_kinds: list[_CpuKind] = []
        for index in range(kinds.n_kinds()):
            cpuset, efficiency, info = kinds.get_info(index)
            cpu_kinds.append((set(cpuset), efficiency, info))

        selected_cpus = _select_windows_cpus(cpu_kinds, available_cpus)

        if (
            selected_cpus is not None
            and selected_cpus != available_cpus
            and len(selected_cpus) > resolved_cpu_num_threads
        ):
            topology.set_cpubind(selected_cpus, flags)

    return resolved_cpu_num_threads
