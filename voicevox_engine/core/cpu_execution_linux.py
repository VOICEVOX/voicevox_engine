"""LinuxのIntelハイブリッドCPU構成を取得し、CPU affinityを操作する。"""

import errno
import os
import platform
import warnings
from pathlib import Path

from voicevox_engine.core.cpu_execution import (
    HybridCpuTopology,
    LinuxCpuExecutionPlan,
)

_CPU_CORE_CPUS_PATH = Path("/sys/devices/cpu_core/cpus")
_CPU_ATOM_CPUS_PATH = Path("/sys/devices/cpu_atom/cpus")
_ONLINE_CPUS_PATH = Path("/sys/devices/system/cpu/online")
_TASK_PATH = Path("/proc/self/task")
_MAX_RETRIES = 3
_X86_MACHINES = {
    "amd64",
    "i386",
    "i486",
    "i586",
    "i686",
    "x86",
    "x86_64",
}


class _LinuxAffinityRace(Exception):
    pass


class _LinuxHybridCpuDetectionUnavailable(RuntimeError):
    pass


def _parse_cpu_list(value: str) -> set[int]:
    text = value.strip()
    if len(text) == 0:
        raise ValueError("LinuxのCPUリストが空です。")
    result: set[int] = set()
    for item in text.split(","):
        if not item.isdecimal():
            if item.count("-") != 1:
                raise ValueError("LinuxのCPUリストの形式が不正です。")
            start_text, end_text = item.split("-")
            if not start_text.isdecimal() or not end_text.isdecimal():
                raise ValueError("LinuxのCPUリストの形式が不正です。")
            start = int(start_text)
            end = int(end_text)
            if start > end:
                raise ValueError("LinuxのCPUリストの範囲が不正です。")
            values = set(range(start, end + 1))
        else:
            values = {int(item)}
        if result & values:
            raise ValueError("LinuxのCPUリストに重複があります。")
        result.update(values)
    return result


def _read_cpu_list(path: Path) -> set[int]:
    try:
        value = path.read_text(encoding="ascii")
    except OSError as error:
        if _is_esrch(error):
            raise _LinuxAffinityRace from error
        raise
    return _parse_cpu_list(value)


def _read_hybrid_cpu_list(path: Path) -> set[int]:
    try:
        value = path.read_text(encoding="ascii")
    except FileNotFoundError as error:
        raise _LinuxHybridCpuDetectionUnavailable from error
    if len(value.strip()) == 0:
        raise _LinuxHybridCpuDetectionUnavailable
    return _parse_cpu_list(value)


def _is_x86() -> bool:
    return platform.machine().lower() in _X86_MACHINES


def _is_esrch(error: BaseException) -> bool:
    return (
        isinstance(error, ProcessLookupError)
        or getattr(error, "errno", None) == errno.ESRCH
    )


def _list_thread_ids() -> tuple[int, ...]:
    try:
        entries = tuple(_TASK_PATH.iterdir())
    except OSError as error:
        if _is_esrch(error):
            raise _LinuxAffinityRace from error
        raise
    thread_ids: list[int] = []
    for entry in entries:
        if not entry.name.isdecimal():
            raise ValueError("LinuxのプロセスTID一覧に不正な名前があります。")
        thread_ids.append(int(entry.name))
    if len(thread_ids) == 0:
        raise RuntimeError("LinuxのプロセスTIDが存在しません。")
    return tuple(sorted(thread_ids))


def _get_thread_affinity(thread_id: int) -> frozenset[int]:
    sched_getaffinity = getattr(os, "sched_getaffinity", None)
    if sched_getaffinity is None:
        raise _LinuxHybridCpuDetectionUnavailable(
            "Linuxのsched_getaffinityが利用できません。"
        )
    try:
        affinity = frozenset(int(cpu_id) for cpu_id in sched_getaffinity(thread_id))
    except OSError as error:
        if error.errno in {errno.ENOSYS, errno.EOPNOTSUPP}:
            raise _LinuxHybridCpuDetectionUnavailable from error
        raise
    if len(affinity) == 0:
        raise ValueError(f"LinuxのTID {thread_id} のCPU affinityが空です。")
    if any(cpu_id < 0 for cpu_id in affinity):
        raise ValueError(f"LinuxのTID {thread_id} のCPU affinityが不正です。")
    return affinity


def _set_thread_affinity(thread_id: int, affinity: frozenset[int]) -> None:
    sched_setaffinity = getattr(os, "sched_setaffinity", None)
    if sched_setaffinity is None:
        raise RuntimeError("Linuxのsched_setaffinityが利用できません。")
    sched_setaffinity(thread_id, affinity)


def _read_thread_affinities(
    thread_ids: tuple[int, ...],
) -> dict[int, frozenset[int]]:
    affinities: dict[int, frozenset[int]] = {}
    for thread_id in thread_ids:
        try:
            affinities[thread_id] = _get_thread_affinity(thread_id)
        except OSError as error:
            if _is_esrch(error):
                raise _LinuxAffinityRace from error
            raise
    return affinities


def _snapshot_detection_state() -> tuple[set[int], dict[int, frozenset[int]]]:
    online_before = _read_cpu_list(_ONLINE_CPUS_PATH)
    thread_ids_before = _list_thread_ids()
    try:
        affinities = _read_thread_affinities(thread_ids_before)
    except _LinuxAffinityRace:
        raise
    online_after = _read_cpu_list(_ONLINE_CPUS_PATH)
    thread_ids_after = _list_thread_ids()
    if online_before != online_after or thread_ids_before != thread_ids_after:
        raise _LinuxAffinityRace
    return online_after, affinities


def _ensure_detection_state_is_stable(
    p_cpus: set[int],
    e_cpus: set[int],
    online_cpus: set[int],
) -> None:
    try:
        current_p_cpus = _read_hybrid_cpu_list(_CPU_CORE_CPUS_PATH)
        current_e_cpus = _read_hybrid_cpu_list(_CPU_ATOM_CPUS_PATH)
    except _LinuxHybridCpuDetectionUnavailable as error:
        raise _LinuxAffinityRace from error
    if current_p_cpus != p_cpus:
        raise _LinuxAffinityRace
    if current_e_cpus != e_cpus:
        raise _LinuxAffinityRace
    if _read_cpu_list(_ONLINE_CPUS_PATH) != online_cpus:
        raise _LinuxAffinityRace


def _detect_linux_hybrid_cpu_topology_once() -> HybridCpuTopology | None:
    p_cpus = _read_hybrid_cpu_list(_CPU_CORE_CPUS_PATH)
    e_cpus = _read_hybrid_cpu_list(_CPU_ATOM_CPUS_PATH)
    if p_cpus & e_cpus:
        raise ValueError("Linuxのcpu_core/cpusとcpu_atom/cpusに重複があります。")
    online_cpus, thread_affinities = _snapshot_detection_state()
    available_cpus = set(online_cpus)
    for affinity in thread_affinities.values():
        available_cpus.intersection_update(affinity)
    if len(available_cpus) == 0:
        _ensure_detection_state_is_stable(p_cpus, e_cpus, online_cpus)
        return None
    unknown_cpus = available_cpus - p_cpus - e_cpus
    if unknown_cpus:
        raise ValueError("Linuxの利用可能CPUにP/E分類のないCPUがあります。")
    available_p_cpus = tuple(sorted(available_cpus & p_cpus))
    available_e_cpus = tuple(sorted(available_cpus & e_cpus))
    if len(available_p_cpus) == 0 or len(available_e_cpus) == 0:
        _ensure_detection_state_is_stable(p_cpus, e_cpus, online_cpus)
        return None
    _ensure_detection_state_is_stable(p_cpus, e_cpus, online_cpus)
    return HybridCpuTopology(available_p_cpus, available_e_cpus)


def detect_linux_hybrid_cpu_topology() -> HybridCpuTopology | None:
    """LinuxのsysfsとTID affinityからIntel P/Eコア構成を検出する。"""
    if not _is_x86():
        return None
    try:
        for _ in range(_MAX_RETRIES):
            try:
                return _detect_linux_hybrid_cpu_topology_once()
            except _LinuxAffinityRace:
                continue
    except _LinuxHybridCpuDetectionUnavailable:
        warnings.warn(
            "LinuxのP/Eコア情報を取得できないため、CPU affinityを変更しません。",
            stacklevel=2,
        )
        return None
    warnings.warn(
        "LinuxのCPU構成が安定しないため、P/Eコアを検出できません。"
        " CPU affinityを変更しません。",
        stacklevel=2,
    )
    return None


def _plan_cpu_ids(plan: LinuxCpuExecutionPlan) -> frozenset[int]:
    if (
        isinstance(plan.cpu_num_threads, bool)
        or not isinstance(plan.cpu_num_threads, int)
        or plan.cpu_num_threads < 1
    ):
        raise ValueError("LinuxのCPUスレッド数は1以上の整数で指定してください。")
    if len(plan.logical_cpu_ids) == 0:
        raise ValueError("Linuxの対象論理CPUが空です。")
    if any(
        isinstance(cpu_id, bool) or not isinstance(cpu_id, int) or cpu_id < 0
        for cpu_id in plan.logical_cpu_ids
    ):
        raise ValueError("Linuxの対象論理CPU IDが不正です。")
    target = frozenset(plan.logical_cpu_ids)
    if len(target) != len(plan.logical_cpu_ids):
        raise ValueError("Linuxの対象論理CPU IDに重複があります。")
    if len(target) <= plan.cpu_num_threads:
        raise ValueError("Linuxの対象論理CPU数はCPUスレッド数より多い必要があります。")
    return target


def _rollback_thread_affinities(
    original_affinities: dict[int, frozenset[int]],
    original_error: Exception,
) -> None:
    try:
        for thread_id, affinity in original_affinities.items():
            try:
                _set_thread_affinity(thread_id, affinity)
                if _get_thread_affinity(thread_id) != affinity:
                    raise RuntimeError(
                        f"LinuxのTID {thread_id} のaffinityを復元できません。"
                    )
            except OSError as error:
                if _is_esrch(error):
                    continue
                raise
    except Exception as rollback_error:
        raise RuntimeError(
            "LinuxのCPU affinity適用に失敗し、ロールバック後の状態を確認できません。"
            f" 元のエラー: {original_error}"
        ) from rollback_error


def apply_linux_cpu_execution_plan(plan: LinuxCpuExecutionPlan) -> None:
    """LinuxのCPU実行計画をプロセス内の全TIDへ適用する。"""
    target = _plan_cpu_ids(plan)
    original_affinities: dict[int, frozenset[int]] = {}
    mutation_started = False
    try:
        for _ in range(_MAX_RETRIES):
            try:
                thread_ids = _list_thread_ids()
            except _LinuxAffinityRace:
                continue
            try:
                current_affinities = _read_thread_affinities(thread_ids)
            except _LinuxAffinityRace:
                continue
            for thread_id, affinity in current_affinities.items():
                if thread_id not in original_affinities:
                    original_affinities[thread_id] = affinity
                if not target.issubset(affinity):
                    raise ValueError(
                        f"LinuxのTID {thread_id} の既存affinityが対象CPU集合を許可していません。"
                    )
            try:
                for thread_id, affinity in current_affinities.items():
                    if affinity != target:
                        mutation_started = True
                        _set_thread_affinity(thread_id, target)
            except OSError as error:
                if _is_esrch(error):
                    continue
                raise
            try:
                final_thread_ids = _list_thread_ids()
            except _LinuxAffinityRace:
                continue
            if final_thread_ids != thread_ids:
                continue
            try:
                final_affinities = _read_thread_affinities(final_thread_ids)
            except _LinuxAffinityRace:
                continue
            if all(affinity == target for affinity in final_affinities.values()):
                return
        raise RuntimeError(
            "LinuxのプロセスTIDが安定しないため、CPU affinityを適用できません。"
        )
    except Exception as error:
        if mutation_started:
            _rollback_thread_affinities(original_affinities, error)
        raise


def validate_linux_cpu_execution_plan(plan: LinuxCpuExecutionPlan) -> None:
    """Linuxの全TIDのaffinityがCPU実行計画と一致することを検証する。"""
    target = _plan_cpu_ids(plan)
    for _ in range(_MAX_RETRIES):
        try:
            thread_ids = _list_thread_ids()
        except _LinuxAffinityRace:
            continue
        try:
            affinities = _read_thread_affinities(thread_ids)
        except _LinuxAffinityRace:
            continue
        try:
            final_thread_ids = _list_thread_ids()
        except _LinuxAffinityRace:
            continue
        if final_thread_ids != thread_ids:
            continue
        if any(affinity != target for affinity in affinities.values()):
            raise RuntimeError(
                "Linuxの全TIDのCPU affinityがCPU実行計画と一致しません。"
            )
        return
    raise RuntimeError(
        "LinuxのプロセスTIDが安定しないため、CPU affinityを検証できません。"
    )
