"""CPU実行設定の解決と適用"""

import os
import sys
import warnings


def _warn_affinity_unavailable(reason: str) -> None:
    warnings.warn(f"{reason}。CPU affinityは変更しません。", stacklevel=2)


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

    if sys.platform not in ("linux", "win32"):
        return resolved_cpu_num_threads

    from pyhwloc.topology import CpuBindFlags, Topology, TopologyFlags

    topology = Topology.from_this_system()
    if sys.platform == "linux":
        topology.set_flags(TopologyFlags.INCLUDE_DISALLOWED)
        flags = CpuBindFlags.THREAD
    else:
        # NOTE: x86検出はWindowsの初期affinityを変更しうるため無効にする。
        topology.set_components("x86")
        flags = CpuBindFlags.PROCESS

    with topology:
        if sys.platform == "win32":
            support = topology.get_support().cpubind
            if not (support.get_thisproc_cpubind and support.set_thisproc_cpubind):
                _warn_affinity_unavailable("WindowsでCPU affinityを設定できません")
                return resolved_cpu_num_threads

        kinds = topology.get_cpukinds()
        if sys.platform == "linux":
            cpu_indices = set(topology.cpuset)
            # NOTE: pyhwloc 3.0.1同梱hwlocはcapacityファイルパスに実OS CPU番号でなく列挙添字を使うため、上流修正コミットdb79bc4c5bda3b4e2e061a53b0e913ec2d683e22を含むpyhwlocへ更新後にこのガードを除去できる。https://github.com/open-mpi/hwloc/commit/db79bc4c5bda3b4e2e061a53b0e913ec2d683e22
            if cpu_indices != set(range(len(cpu_indices))):
                _warn_affinity_unavailable(
                    "LinuxのCPU番号に欠番がありCPU capacityを正しく取得できません"
                )
                return resolved_cpu_num_threads

            kind_infos = [kinds.get_info(index) for index in range(kinds.n_kinds())]
            if len(kind_infos) == 0 or any(
                "LinuxCapacity" not in info for _, _, info in kind_infos
            ):
                _warn_affinity_unavailable("LinuxのCPU capacityを取得できません")
                return resolved_cpu_num_threads

            capacities = [
                (cpuset, int(info["LinuxCapacity"])) for cpuset, _, info in kind_infos
            ]
            highest_capacity = max(capacity for _, capacity in capacities)
            candidate_cpus = {
                cpu
                for cpuset, capacity in capacities
                if capacity * 2 >= highest_capacity
                for cpu in cpuset
            }
        else:
            candidate_cpus = set(kinds.get_info(kinds.n_kinds() - 1)[0])

        available_cpus = set(topology.get_cpubind(flags))
        selected_cpus = candidate_cpus & available_cpus
        if (
            selected_cpus != available_cpus
            and len(selected_cpus) > resolved_cpu_num_threads
        ):
            topology.set_cpubind(selected_cpus, flags)

    return resolved_cpu_num_threads
