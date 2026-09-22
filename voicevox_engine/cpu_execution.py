"""CPUスレッド数の決定とCPU affinityの設定"""

import os
import sys
import warnings


def configure_cpu_execution(cpu_num_threads: int | None) -> int:
    """
    CPUスレッド数を決定して返し、実行環境とCPU構成に応じてCPU affinityを制限する。

    CPUスレッド数は、指定値が`None`または`0`なら論理コア数の半分の切り上げとする。
    論理コア数を取得できない場合は`0`とする。

    CPUスレッド数が`0`でなく、OSがLinuxまたはWindowsの場合に、CPU affinityを変えて高性能CPUのみを使おうとする。
    Linuxでは、全CPUの最大値の半分以上のcapacityを持つCPUを候補とする。
    Windowsでは、最も高性能なEfficiencyClassを持つCPUを候補とする。
    元のCPU affinityと候補CPUの積集合の数が、指定したスレッド数を上回る場合にCPU affinityを変更する。
    """
    resolved_cpu_num_threads = _resolve_cpu_num_threads(cpu_num_threads)
    if resolved_cpu_num_threads == 0:
        return resolved_cpu_num_threads

    if sys.platform not in ("linux", "win32"):
        return resolved_cpu_num_threads

    _configure_cpu_affinity(resolved_cpu_num_threads)
    return resolved_cpu_num_threads


def _resolve_cpu_num_threads(cpu_num_threads: int | None) -> int:
    """指定値からCPUスレッド数を決定して返す。"""
    if cpu_num_threads is not None and cpu_num_threads != 0:
        return cpu_num_threads

    msg = "cpu_num_threads is set to 0. Setting it to an appropriate value."
    warnings.warn(msg, stacklevel=1)

    logical_cpu_count = os.cpu_count()
    if logical_cpu_count is None:
        _warn_affinity_unavailable("the logical core count is unavailable")
        return 0
    return (logical_cpu_count + 1) // 2


def _configure_cpu_affinity(resolved_cpu_num_threads: int) -> None:
    """必要に応じて、高性能なCPUを優先して使うようCPU affinityを制限する。"""
    from pyhwloc.topology import CpuBindFlags, Topology, TopologyFlags

    topology = Topology.from_this_system()
    if sys.platform == "linux":
        # NOTE: 最大capacityの値を得るために全CPUを対象にする。
        topology.set_flags(TopologyFlags.INCLUDE_DISALLOWED)
        flags = CpuBindFlags.THREAD
    else:
        # NOTE: x86検出はWindowsの初期affinityを変更しうるため無効にする。
        topology.set_components("x86")
        flags = CpuBindFlags.PROCESS

    with topology:
        kinds = topology.get_cpukinds()
        if sys.platform == "win32":
            support = topology.get_support().cpubind
            if not (support.get_thisproc_cpubind and support.set_thisproc_cpubind):
                _warn_affinity_unavailable(
                    "CPU binding is unavailable in this Windows environment"
                )
                return
            candidate_cpus = set(kinds.get_info(kinds.n_kinds() - 1)[0])
        else:
            cpu_indices = set(topology.cpuset)
            # NOTE: hwlocはCPU番号が0から連続していないとLinuxCapacityを正しく取得できないバグがあるため見送る
            if cpu_indices != set(range(len(cpu_indices))):
                _warn_affinity_unavailable(
                    "gaps in Linux CPU numbering prevent CPU capacity from being read correctly"
                )
                return

            kind_infos = [kinds.get_info(index) for index in range(kinds.n_kinds())]
            if len(kind_infos) == 0 or any(
                "LinuxCapacity" not in info for _, _, info in kind_infos
            ):
                _warn_affinity_unavailable("Linux CPU capacity is unavailable")
                return

            # capacityの大きさで使うCPUを選ぶ
            capacities = [
                (cpuset, int(info["LinuxCapacity"])) for cpuset, _, info in kind_infos
            ]
            highest_capacity = max(capacity for _, capacity in capacities)
            candidate_cpus = {
                cpu
                for cpuset, capacity in capacities
                if capacity >= highest_capacity / 2
                for cpu in cpuset
            }

        # CPU affinityを設定する
        available_cpus = set(topology.get_cpubind(flags))
        selected_cpus = candidate_cpus & available_cpus
        if (
            selected_cpus != available_cpus
            and len(selected_cpus) > resolved_cpu_num_threads
        ):
            topology.set_cpubind(selected_cpus, flags)


def _warn_affinity_unavailable(reason: str) -> None:
    warnings.warn(f"CPU affinity is left unchanged because {reason}.", stacklevel=2)
