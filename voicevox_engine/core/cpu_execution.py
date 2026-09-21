"""CPU実行設定の解決と適用"""

import os
import platform
import warnings

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


def _select_linux_cpus(
    cpu_kinds: list[_CpuKind], available_cpus: set[int], pu_os_indices: list[int]
) -> set[int] | None:
    if set(pu_os_indices) != set(range(len(pu_os_indices))):
        _warn_affinity_unavailable("LinuxCapacityと論理CPU番号の対応を確認できません")
        return None

    capacity_kinds: list[tuple[set[int], int]] = []
    for cpus, _, info in cpu_kinds:
        matching_cpus = cpus & available_cpus
        if len(matching_cpus) == 0:
            continue
        capacity_text = info.get("LinuxCapacity")
        if capacity_text is None:
            _warn_affinity_unavailable("LinuxCapacityを取得できません")
            return None
        capacity = int(capacity_text)
        if capacity == 0:
            _warn_affinity_unavailable("LinuxCapacityを取得できません")
            return None
        if capacity < 0:
            raise ValueError("LinuxCapacityは正の整数である必要があります。")
        capacity_kinds.append((matching_cpus, capacity))

    covered_cpus = set().union(*(cpus for cpus, _ in capacity_kinds))
    if covered_cpus != available_cpus:
        _warn_affinity_unavailable("利用可能な全論理CPUのLinuxCapacityを取得できません")
        return None

    highest_capacity = max(capacity for _, capacity in capacity_kinds)
    return set().union(
        *(cpus for cpus, capacity in capacity_kinds if capacity * 2 >= highest_capacity)
    )


def _resolve_cpu_num_threads(cpu_num_threads: int | None) -> int:
    if cpu_num_threads is not None and cpu_num_threads != 0:
        if not 1 <= cpu_num_threads <= 65535:
            raise ValueError(
                "cpu_num_threadsは0、または1以上65535以下で指定してください。"
            )
        return cpu_num_threads

    logical_cpu_count = os.cpu_count()
    if logical_cpu_count is None:
        _warn_affinity_unavailable("CPUスレッド数を決定できません")
        return 0
    return logical_cpu_count // 2


def configure_cpu_execution(cpu_num_threads: int | None) -> int:
    """
    CPUスレッド数を決定し、条件に合えば高性能CPUへCPU affinityを設定する。

    未指定または0の場合は論理CPU数の半分を小数点以下切り捨てで使い、論理CPU数を取得できなければ警告して0を返す。
    Windowsでは高いCPU性能クラス、Linuxでは最大のLinuxCapacityの半分以上を持つ論理CPUを候補とし、既存の許可CPUの範囲で候補数が決定したスレッド数を超える場合にaffinityを設定する。
    """
    resolved_cpu_num_threads = _resolve_cpu_num_threads(cpu_num_threads)
    if resolved_cpu_num_threads == 0:
        return resolved_cpu_num_threads

    system = platform.system()
    if system not in ("Windows", "Linux"):
        return resolved_cpu_num_threads

    from pyhwloc.topology import CpuBindFlags, Topology

    flags = CpuBindFlags.PROCESS if system == "Windows" else CpuBindFlags.THREAD
    topology = Topology.from_this_system()
    if system == "Windows":
        topology.set_components("x86")

    with topology:
        support = topology.get_support().cpubind
        if system == "Windows":
            can_bind = support.get_thisproc_cpubind and support.set_thisproc_cpubind
        else:
            can_bind = support.get_thisthread_cpubind and support.set_thisthread_cpubind
        if not can_bind:
            _warn_affinity_unavailable(f"{system}でCPU affinityを設定できません")
            return resolved_cpu_num_threads

        available_cpus = set(topology.allowed_cpuset) & set(topology.get_cpubind(flags))
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
