"""CPU実行計画の値と選択処理"""

import platform
from dataclasses import dataclass

import psutil

from voicevox_engine.utility.error_utility import UnreachableError


@dataclass(frozen=True)
class HybridCpuTopology:
    """PコアとEコアの論理CPU構成を表す。"""

    p_logical_cpu_ids: tuple[int, ...]
    e_logical_cpu_ids: tuple[int, ...]


@dataclass(frozen=True)
class LegacyCpuExecutionPlan:
    """レガシーCPU実行計画を表す。"""

    cpu_num_threads: int


@dataclass(frozen=True)
class WindowsCpuExecutionPlan:
    """WindowsのCPU実行計画を表す。"""

    cpu_num_threads: int
    logical_processor_indices: tuple[int, ...]


@dataclass(frozen=True)
class LinuxCpuExecutionPlan:
    """LinuxのCPU実行計画を表す。"""

    cpu_num_threads: int
    logical_cpu_ids: tuple[int, ...]


type CpuExecutionPlan = (
    LegacyCpuExecutionPlan | WindowsCpuExecutionPlan | LinuxCpuExecutionPlan
)


def _validate_cpu_num_threads(cpu_num_threads: int | None) -> int | None:
    if cpu_num_threads is None:
        return None
    if isinstance(cpu_num_threads, bool) or not isinstance(cpu_num_threads, int):
        raise ValueError("cpu_num_threadsは整数、None、または0で指定してください。")
    if cpu_num_threads == 0:
        return None
    if not 1 <= cpu_num_threads <= 65535:
        raise ValueError("cpu_num_threadsは0、または1以上65535以下で指定してください。")
    return cpu_num_threads


def _validate_cpu_count(cpu_count: int | None, name: str) -> int | None:
    if cpu_count is None:
        return None
    if isinstance(cpu_count, bool) or not isinstance(cpu_count, int) or cpu_count < 1:
        raise ValueError(f"{name}はNoneまたは1以上の整数で指定してください。")
    return cpu_count


def _normalize_logical_cpu_ids(
    logical_cpu_ids: tuple[int, ...], name: str
) -> tuple[int, ...]:
    if len(logical_cpu_ids) == 0:
        raise ValueError(f"{name}の論理CPUが1つ以上必要です。")
    if any(
        isinstance(logical_cpu_id, bool)
        or not isinstance(logical_cpu_id, int)
        or logical_cpu_id < 0
        for logical_cpu_id in logical_cpu_ids
    ):
        raise ValueError(f"{name}の論理CPU IDは0以上の整数で指定してください。")
    normalized_ids = tuple(sorted(logical_cpu_ids))
    if len(set(normalized_ids)) != len(normalized_ids):
        raise ValueError(f"{name}の論理CPU IDに重複があります。")
    return normalized_ids


def _normalize_topology(
    topology: HybridCpuTopology,
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    p_logical_cpu_ids = _normalize_logical_cpu_ids(
        topology.p_logical_cpu_ids,
        "Pコア",
    )
    e_logical_cpu_ids = _normalize_logical_cpu_ids(
        topology.e_logical_cpu_ids,
        "Eコア",
    )
    if set(p_logical_cpu_ids) & set(e_logical_cpu_ids):
        raise ValueError("PコアとEコアの論理CPU IDに重複があります。")
    return p_logical_cpu_ids, e_logical_cpu_ids


def _resolve_cpu_num_threads(
    requested_cpu_num_threads: int | None,
    logical_cpu_count: int | None,
) -> int:
    validated_cpu_num_threads = _validate_cpu_num_threads(requested_cpu_num_threads)
    if validated_cpu_num_threads is not None:
        return validated_cpu_num_threads
    if logical_cpu_count is None:
        return 0
    return logical_cpu_count // 2


def _create_hybrid_cpu_execution_values(
    cpu_num_threads: int | None,
    topology: HybridCpuTopology,
) -> tuple[int, tuple[int, ...] | None]:
    p_logical_cpu_ids, e_logical_cpu_ids = _normalize_topology(topology)
    resolved_cpu_num_threads = _resolve_cpu_num_threads(
        cpu_num_threads,
        len(p_logical_cpu_ids) + len(e_logical_cpu_ids),
    )
    if len(p_logical_cpu_ids) <= resolved_cpu_num_threads:
        return resolved_cpu_num_threads, None
    return resolved_cpu_num_threads, p_logical_cpu_ids


def create_legacy_cpu_execution_plan(
    cpu_num_threads: int | None,
    logical_cpu_count: int | None,
) -> LegacyCpuExecutionPlan:
    """レガシーCPU実行計画を生成する。"""
    validated_cpu_num_threads = _validate_cpu_num_threads(cpu_num_threads)
    if validated_cpu_num_threads is not None:
        return LegacyCpuExecutionPlan(validated_cpu_num_threads)
    logical_cpu_count = _validate_cpu_count(logical_cpu_count, "logical_cpu_count")
    return LegacyCpuExecutionPlan(_resolve_cpu_num_threads(None, logical_cpu_count))


def create_windows_cpu_execution_plan(
    cpu_num_threads: int | None,
    topology: HybridCpuTopology,
) -> CpuExecutionPlan:
    """WindowsのCPU実行計画を生成する。"""
    resolved_cpu_num_threads, logical_processor_indices = (
        _create_hybrid_cpu_execution_values(cpu_num_threads, topology)
    )
    if logical_processor_indices is None:
        return LegacyCpuExecutionPlan(resolved_cpu_num_threads)
    return WindowsCpuExecutionPlan(resolved_cpu_num_threads, logical_processor_indices)


def create_linux_cpu_execution_plan(
    cpu_num_threads: int | None,
    topology: HybridCpuTopology,
) -> CpuExecutionPlan:
    """LinuxのCPU実行計画を生成する。"""
    resolved_cpu_num_threads, logical_cpu_ids = _create_hybrid_cpu_execution_values(
        cpu_num_threads, topology
    )
    if logical_cpu_ids is None:
        return LegacyCpuExecutionPlan(resolved_cpu_num_threads)
    return LinuxCpuExecutionPlan(resolved_cpu_num_threads, logical_cpu_ids)


def _create_legacy_cpu_execution_plan_from_system(
    cpu_num_threads: int | None,
) -> LegacyCpuExecutionPlan:
    if cpu_num_threads is not None:
        return LegacyCpuExecutionPlan(cpu_num_threads)
    return create_legacy_cpu_execution_plan(
        cpu_num_threads,
        psutil.cpu_count(logical=True),
    )


def create_cpu_execution_plan(
    cpu_num_threads: int | None,
) -> CpuExecutionPlan:
    """実行環境に応じたCPU実行計画を生成する。"""
    validated_cpu_num_threads = _validate_cpu_num_threads(cpu_num_threads)
    system = platform.system()
    if system == "Windows":
        from voicevox_engine.core.cpu_execution_windows import (
            detect_windows_hybrid_cpu_topology,
        )

        topology = detect_windows_hybrid_cpu_topology()
        if topology is None:
            return _create_legacy_cpu_execution_plan_from_system(
                validated_cpu_num_threads
            )
        return create_windows_cpu_execution_plan(validated_cpu_num_threads, topology)
    if system == "Linux":
        from voicevox_engine.core.cpu_execution_linux import (
            detect_linux_hybrid_cpu_topology,
        )

        topology = detect_linux_hybrid_cpu_topology()
        if topology is None:
            return _create_legacy_cpu_execution_plan_from_system(
                validated_cpu_num_threads
            )
        return create_linux_cpu_execution_plan(validated_cpu_num_threads, topology)
    if system == "Darwin":
        return _create_legacy_cpu_execution_plan_from_system(validated_cpu_num_threads)
    return _create_legacy_cpu_execution_plan_from_system(validated_cpu_num_threads)


def apply_cpu_execution_plan(plan: CpuExecutionPlan) -> None:
    """CPU実行計画を現在のプロセスへ適用する。"""
    if isinstance(plan, LegacyCpuExecutionPlan):
        return
    if isinstance(plan, WindowsCpuExecutionPlan):
        from voicevox_engine.core.cpu_execution_windows import (
            apply_windows_cpu_execution_plan,
        )

        apply_windows_cpu_execution_plan(plan)
        return
    if isinstance(plan, LinuxCpuExecutionPlan):
        from voicevox_engine.core.cpu_execution_linux import (
            apply_linux_cpu_execution_plan,
        )

        apply_linux_cpu_execution_plan(plan)
        return
    raise UnreachableError("CPU実行計画の型が不正です。")


def validate_cpu_execution_plan(plan: CpuExecutionPlan) -> None:
    """CPU実行計画が現在のCPU affinityへ反映されていることを検証する。"""
    if isinstance(plan, LegacyCpuExecutionPlan):
        return
    if isinstance(plan, WindowsCpuExecutionPlan):
        from voicevox_engine.core.cpu_execution_windows import (
            validate_windows_cpu_execution_plan,
        )

        validate_windows_cpu_execution_plan(plan)
        return
    if isinstance(plan, LinuxCpuExecutionPlan):
        from voicevox_engine.core.cpu_execution_linux import (
            validate_linux_cpu_execution_plan,
        )

        validate_linux_cpu_execution_plan(plan)
        return
    raise UnreachableError("CPU実行計画の型が不正です。")
