"""LinuxのIntelハイブリッドCPU構成を取得し、CPU affinityを操作する。"""

import os
import platform
from pathlib import Path

_CPU_CORE_CPUS_PATH = Path("/sys/bus/event_source/devices/cpu_core/cpus")
_CPU_ATOM_CPUS_PATH = Path("/sys/bus/event_source/devices/cpu_atom/cpus")
_TASK_PATH = Path("/proc/self/task")
_X86_MACHINES = {
    "amd64",
    "i386",
    "i486",
    "i586",
    "i686",
    "x86",
    "x86_64",
}


def _parse_cpu_list(value: str) -> set[int]:
    text = value.strip()
    if text == "":
        raise ValueError("LinuxのCPUリストが空です。")

    result: set[int] = set()
    for item in text.split(","):
        if "-" in item:
            parts = item.split("-")
            if len(parts) != 2 or not all(part.isdecimal() for part in parts):
                raise ValueError("LinuxのCPUリストの形式が不正です。")
            start, end = map(int, parts)
            if start > end:
                raise ValueError("LinuxのCPUリストの範囲が不正です。")
            values = set(range(start, end + 1))
        elif item.isdecimal():
            values = {int(item)}
        else:
            raise ValueError("LinuxのCPUリストの形式が不正です。")

        if result & values:
            raise ValueError("LinuxのCPUリストに重複があります。")
        result.update(values)

    return result


def _read_hybrid_cpu_list(path: Path) -> set[int]:
    value = path.read_text(encoding="ascii")
    if value.strip() == "":
        return set()
    return _parse_cpu_list(value)


def _is_x86() -> bool:
    return platform.machine().lower() in _X86_MACHINES


def _list_thread_ids() -> tuple[int, ...]:
    thread_ids = tuple(
        int(entry.name) for entry in _TASK_PATH.iterdir() if entry.name.isdecimal()
    )
    if len(thread_ids) == 0:
        raise RuntimeError("LinuxのプロセスTIDが存在しません。")
    return tuple(sorted(thread_ids))


def _get_thread_affinity(thread_id: int) -> frozenset[int]:
    sched_getaffinity = getattr(os, "sched_getaffinity", None)
    if sched_getaffinity is None:
        raise RuntimeError("Linuxのsched_getaffinityが利用できません。")
    return frozenset(sched_getaffinity(thread_id))


def _set_thread_affinity(thread_id: int, affinity: frozenset[int]) -> None:
    sched_setaffinity = getattr(os, "sched_setaffinity", None)
    if sched_setaffinity is None:
        raise RuntimeError("Linuxのsched_setaffinityが利用できません。")
    sched_setaffinity(thread_id, affinity)


def _read_thread_affinities(
    thread_ids: tuple[int, ...],
) -> dict[int, frozenset[int]]:
    return {thread_id: _get_thread_affinity(thread_id) for thread_id in thread_ids}


def configure_linux_cpu_execution(cpu_num_threads: int) -> None:
    """利用可能な論理PコアへLinuxの全TIDを一度制限する。"""
    if not _is_x86():
        return

    try:
        p_cpus = _read_hybrid_cpu_list(_CPU_CORE_CPUS_PATH)
        e_cpus = _read_hybrid_cpu_list(_CPU_ATOM_CPUS_PATH)
        if not p_cpus or not e_cpus or p_cpus & e_cpus:
            return

        thread_ids = _list_thread_ids()
        thread_affinities = _read_thread_affinities(thread_ids)
        available_cpus = set(p_cpus | e_cpus)
        for affinity in thread_affinities.values():
            available_cpus.intersection_update(affinity)

        available_p_cpus = available_cpus & p_cpus
        available_e_cpus = available_cpus & e_cpus
        if not available_p_cpus or not available_e_cpus:
            return

        if len(available_p_cpus) <= cpu_num_threads:
            return

        target = frozenset(available_p_cpus)
        for thread_id in thread_ids:
            _set_thread_affinity(thread_id, target)
    except FileNotFoundError:
        return
