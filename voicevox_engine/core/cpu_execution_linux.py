"""LinuxのIntelハイブリッドCPU構成を取得し、CPU affinityを操作する。"""

import os
from pathlib import Path

_CPU_CORE_CPUS_PATH = Path("/sys/bus/event_source/devices/cpu_core/cpus")
_CPU_ATOM_CPUS_PATH = Path("/sys/bus/event_source/devices/cpu_atom/cpus")


def _parse_cpu_list(value: str) -> set[int]:
    result: set[int] = set()
    for item in value.split(","):
        if "-" in item:
            start, end = map(int, item.split("-"))
            if start > end:
                raise ValueError("LinuxのCPUリストの範囲が不正です。")
            result.update(range(start, end + 1))
        else:
            result.add(int(item))

    return result


def _read_hybrid_cpu_list(path: Path) -> set[int]:
    value = path.read_text(encoding="ascii")
    if value.strip() == "":
        return set()
    return _parse_cpu_list(value)


def configure_linux_cpu_execution(cpu_num_threads: int) -> None:
    """利用可能な論理Pコアへ呼び出し元TIDのCPU affinityを一度制限する。"""
    try:
        p_cpus = _read_hybrid_cpu_list(_CPU_CORE_CPUS_PATH)
        e_cpus = _read_hybrid_cpu_list(_CPU_ATOM_CPUS_PATH)
    except FileNotFoundError:
        return

    if not p_cpus or not e_cpus:
        return

    sched_getaffinity_name = "sched_getaffinity"
    available_cpus = getattr(os, sched_getaffinity_name)(0)
    available_p_cpus = available_cpus & p_cpus
    available_e_cpus = available_cpus & e_cpus
    if not available_e_cpus:
        return
    if len(available_p_cpus) <= cpu_num_threads:
        return

    sched_setaffinity_name = "sched_setaffinity"
    getattr(os, sched_setaffinity_name)(0, available_p_cpus)
