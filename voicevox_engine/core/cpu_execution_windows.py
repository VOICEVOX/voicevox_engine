"""WindowsのハイブリッドCPU構成を取得し、CPU affinityを操作する。"""

import ctypes
import warnings
from dataclasses import dataclass
from typing import Any, cast

from voicevox_engine.core.cpu_execution import (
    HybridCpuTopology,
    WindowsCpuExecutionPlan,
)

_ERROR_INSUFFICIENT_BUFFER = 122
_ERROR_NOT_SUPPORTED = 50
_ERROR_CALL_NOT_IMPLEMENTED = 120
_CPU_SET_INFORMATION_TYPE_CPU_SET = 0
_MAX_PROCESSOR_GROUP_SIZE = 64
_DWORD = ctypes.c_uint32
_WORD = ctypes.c_uint16
_HANDLE = ctypes.c_void_p
_BOOL = ctypes.c_int32


class _WindowsHybridCpuDetectionUnavailable(RuntimeError):
    pass


class _SystemCpuSetInformationHeader(ctypes.Structure):
    _fields_ = [("Size", _DWORD), ("Type", _DWORD)]


class _CpuSetInformationData(ctypes.Structure):
    _fields_ = [
        ("Id", _DWORD),
        ("Group", _WORD),
        ("LogicalProcessorIndex", ctypes.c_ubyte),
        ("CoreIndex", ctypes.c_ubyte),
        ("LastLevelCacheIndex", ctypes.c_ubyte),
        ("NumaNodeIndex", ctypes.c_ubyte),
        ("EfficiencyClass", ctypes.c_ubyte),
        ("Flags", ctypes.c_ubyte),
        ("SchedulingClass", _DWORD),
        ("AllocationTag", ctypes.c_ulonglong),
    ]


class _SystemCpuSetInformation(ctypes.Structure):
    _fields_ = [
        ("Size", _DWORD),
        ("Type", _DWORD),
        ("CpuSet", _CpuSetInformationData),
    ]


@dataclass(frozen=True)
class _WindowsCpuSetRecord:
    cpu_set_id: int
    group: int
    logical_processor_index: int
    efficiency_class: int
    allocated: bool
    allocated_to_target_process: bool


class _WindowsApi:
    def __init__(self) -> None:
        windll = getattr(ctypes, "WinDLL", None)
        if windll is None:
            raise _WindowsHybridCpuDetectionUnavailable(
                "WindowsのCPU Set APIを読み込めません。"
            )
        kernel32 = windll("kernel32", use_last_error=True)
        try:
            self._get_current_process: Any = _get_library_function(
                kernel32, "GetCurrentProcess"
            )
            self._get_system_cpu_set_information: Any = _get_library_function(
                kernel32, "GetSystemCpuSetInformation"
            )
            self._get_process_affinity_mask: Any = _get_library_function(
                kernel32, "GetProcessAffinityMask"
            )
            self._set_process_affinity_mask: Any = _get_library_function(
                kernel32, "SetProcessAffinityMask"
            )
            self._get_active_processor_group_count: Any = _get_library_function(
                kernel32, "GetActiveProcessorGroupCount"
            )
            self._get_process_group_affinity: Any = _get_library_function(
                kernel32, "GetProcessGroupAffinity"
            )
        except AttributeError as error:
            raise _WindowsHybridCpuDetectionUnavailable(
                "WindowsのCPU Set APIが利用できません。"
            ) from error

        handle_type = _HANDLE
        mask_type = ctypes.c_size_t
        self._get_current_process.argtypes = []
        self._get_current_process.restype = handle_type
        self._get_system_cpu_set_information.argtypes = [
            ctypes.c_void_p,
            _DWORD,
            ctypes.POINTER(_DWORD),
            handle_type,
            _DWORD,
        ]
        self._get_system_cpu_set_information.restype = _BOOL
        self._get_process_affinity_mask.argtypes = [
            handle_type,
            ctypes.POINTER(mask_type),
            ctypes.POINTER(mask_type),
        ]
        self._get_process_affinity_mask.restype = _BOOL
        self._set_process_affinity_mask.argtypes = [handle_type, mask_type]
        self._set_process_affinity_mask.restype = _BOOL
        self._get_active_processor_group_count.argtypes = []
        self._get_active_processor_group_count.restype = _WORD
        self._get_process_group_affinity.argtypes = [
            handle_type,
            ctypes.POINTER(_WORD),
            ctypes.POINTER(_WORD),
        ]
        self._get_process_group_affinity.restype = _BOOL

    @staticmethod
    def _last_error_code() -> int:
        error_function_name = "get_last_error"
        get_last_error = getattr(ctypes, error_function_name)
        return int(get_last_error())

    @classmethod
    def _last_error(cls) -> OSError:
        error_code = cls._last_error_code()
        format_error = getattr(ctypes, "FormatError", None)
        if format_error is None:
            return OSError(error_code)
        return OSError(error_code, format_error(error_code))

    def _current_process(self) -> _HANDLE:
        return cast(_HANDLE, self._get_current_process())

    def get_system_cpu_set_information(self) -> bytes:
        """CPU Set情報を可変長レコード列として取得する。"""
        process = self._current_process()
        for _ in range(3):
            required_length = _DWORD()
            result = self._get_system_cpu_set_information(
                None,
                0,
                ctypes.byref(required_length),
                process,
                0,
            )
            if not result:
                if self._last_error_code() != _ERROR_INSUFFICIENT_BUFFER:
                    raise self._last_error()
                if required_length.value == 0:
                    raise ValueError("WindowsのCPU Set情報の長さを取得できません。")
            if required_length.value == 0:
                raise ValueError("WindowsのCPU Set情報の長さが不正です。")
            buffer = (ctypes.c_ubyte * required_length.value)()
            returned_length = _DWORD()
            result = self._get_system_cpu_set_information(
                ctypes.cast(buffer, ctypes.c_void_p),
                required_length.value,
                ctypes.byref(returned_length),
                process,
                0,
            )
            if result:
                if returned_length.value > required_length.value:
                    raise ValueError("WindowsのCPU Set情報の長さが不正です。")
                if returned_length.value == 0:
                    raise ValueError("WindowsのCPU Set情報の長さが不正です。")
                return bytes(buffer[: returned_length.value])
            if self._last_error_code() != _ERROR_INSUFFICIENT_BUFFER:
                raise self._last_error()
        raise _WindowsHybridCpuDetectionUnavailable(
            "WindowsのCPU Set情報の長さが安定しないため取得できません。"
        )

    def get_process_affinity_mask(self) -> tuple[int, int]:
        """現在のプロセスとシステムのhard affinity maskを取得する。"""
        process_mask = ctypes.c_size_t()
        system_mask = ctypes.c_size_t()
        result = self._get_process_affinity_mask(
            self._current_process(),
            ctypes.byref(process_mask),
            ctypes.byref(system_mask),
        )
        if not result:
            raise self._last_error()
        return int(process_mask.value), int(system_mask.value)

    def set_process_affinity_mask(self, mask: int) -> None:
        """現在のプロセスのhard affinity maskを設定する。"""
        result = self._set_process_affinity_mask(self._current_process(), mask)
        if not result:
            raise self._last_error()

    def get_active_processor_group_count(self) -> int:
        """アクティブなProcessor Group数を取得する。"""
        count = int(self._get_active_processor_group_count())
        if count < 1:
            raise self._last_error()
        return count

    def get_process_group_affinity(self) -> tuple[int, ...]:
        """現在のプロセスに割り当てられたProcessor Groupを取得する。"""
        process = self._current_process()
        group_count = _WORD()
        result = self._get_process_group_affinity(
            process,
            ctypes.byref(group_count),
            None,
        )
        if not result and self._last_error_code() != _ERROR_INSUFFICIENT_BUFFER:
            raise self._last_error()
        if group_count.value == 0:
            return ()
        groups = (_WORD * group_count.value)()
        result = self._get_process_group_affinity(
            process,
            ctypes.byref(group_count),
            groups,
        )
        if not result:
            raise self._last_error()
        return tuple(int(group) for group in groups[: group_count.value])


def _get_windows_api() -> _WindowsApi:
    return _WindowsApi()


def _get_library_function(library: Any, name: str) -> Any:
    return getattr(library, name)


def _parse_cpu_set_records(buffer: bytes) -> tuple[_WindowsCpuSetRecord, ...]:
    records: list[_WindowsCpuSetRecord] = []
    offset = 0
    minimum_size = ctypes.sizeof(_SystemCpuSetInformation)
    header_size = ctypes.sizeof(_SystemCpuSetInformationHeader)
    while offset < len(buffer):
        if len(buffer) - offset < header_size:
            raise ValueError("WindowsのCPU Set情報レコードのヘッダーが不完全です。")
        header = _SystemCpuSetInformationHeader.from_buffer_copy(buffer, offset)
        size = int(header.Size)
        if size < header_size or offset + size > len(buffer):
            raise ValueError("WindowsのCPU Set情報レコードの長さが不正です。")
        if int(header.Type) == _CPU_SET_INFORMATION_TYPE_CPU_SET:
            if size < minimum_size:
                raise ValueError("WindowsのCPU Set情報レコードの長さが不正です。")
            information = _SystemCpuSetInformation.from_buffer_copy(buffer, offset)
            cpu_set = information.CpuSet
            records.append(
                _WindowsCpuSetRecord(
                    int(cpu_set.Id),
                    int(cpu_set.Group),
                    int(cpu_set.LogicalProcessorIndex),
                    int(cpu_set.EfficiencyClass),
                    bool(cpu_set.Flags & 0b10),
                    bool(cpu_set.Flags & 0b100),
                )
            )
        offset += size
    return tuple(records)


def _validate_cpu_set_records(
    records: tuple[_WindowsCpuSetRecord, ...],
) -> tuple[_WindowsCpuSetRecord, ...]:
    cpu_set_ids: set[int] = set()
    processor_keys: set[tuple[int, int]] = set()
    available_records: list[_WindowsCpuSetRecord] = []
    for record in records:
        if record.logical_processor_index >= _MAX_PROCESSOR_GROUP_SIZE:
            raise ValueError("Windowsの論理プロセッサ番号が不正です。")
        if record.cpu_set_id in cpu_set_ids:
            raise ValueError("WindowsのCPU Set IDに重複があります。")
        processor_key = (record.group, record.logical_processor_index)
        if processor_key in processor_keys:
            raise ValueError("WindowsのGroupと論理プロセッサ番号に重複があります。")
        cpu_set_ids.add(record.cpu_set_id)
        processor_keys.add(processor_key)
        if record.allocated and not record.allocated_to_target_process:
            continue
        available_records.append(record)
    return tuple(available_records)


def _filter_process_records(
    records: tuple[_WindowsCpuSetRecord, ...],
    process_mask: int,
    process_groups: tuple[int, ...],
) -> tuple[_WindowsCpuSetRecord, ...]:
    if len(process_groups) != 1 or process_mask == 0:
        return records
    process_group = process_groups[0]
    return tuple(
        record
        for record in records
        if record.group == process_group
        and process_mask & (1 << record.logical_processor_index)
    )


def _validate_process_groups(
    active_group_count: int,
    process_groups: tuple[int, ...],
) -> None:
    if active_group_count < 1:
        raise ValueError("WindowsのProcessor Group数が不正です。")
    if len(process_groups) == 0:
        raise ValueError("WindowsのプロセスProcessor Groupが空です。")
    if any(
        isinstance(group, bool) or not isinstance(group, int)
        for group in process_groups
    ):
        raise ValueError("WindowsのプロセスProcessor Group番号が不正です。")
    if len(set(process_groups)) != len(process_groups):
        raise ValueError("WindowsのプロセスProcessor Groupに重複があります。")
    if any(not 0 <= group < active_group_count for group in process_groups):
        raise RuntimeError("WindowsのプロセスProcessor Group番号が不正です。")


def _windows_error_code(error: OSError) -> int | None:
    winerror = getattr(error, "winerror", None)
    if isinstance(winerror, int) and not isinstance(winerror, bool):
        return winerror
    error_number = getattr(error, "errno", None)
    if isinstance(error_number, int) and not isinstance(error_number, bool):
        return error_number
    return None


def _is_windows_hybrid_detection_unavailable_error(error: OSError) -> bool:
    return _windows_error_code(error) in {
        _ERROR_NOT_SUPPORTED,
        _ERROR_CALL_NOT_IMPLEMENTED,
    }


def _topology_from_records(
    records: tuple[_WindowsCpuSetRecord, ...],
    p_efficiency_class: int,
) -> HybridCpuTopology | None:
    p_logical_cpu_ids = tuple(
        sorted(
            record.logical_processor_index
            for record in records
            if record.efficiency_class == p_efficiency_class
        )
    )
    e_logical_cpu_ids = tuple(
        sorted(
            record.logical_processor_index
            for record in records
            if record.efficiency_class != p_efficiency_class
        )
    )
    if len(p_logical_cpu_ids) == 0 or len(e_logical_cpu_ids) == 0:
        return None
    return HybridCpuTopology(p_logical_cpu_ids, e_logical_cpu_ids)


def _detect_windows_hybrid_cpu_topology() -> HybridCpuTopology | None:
    api = _get_windows_api()
    system_records = _parse_cpu_set_records(api.get_system_cpu_set_information())
    records = _validate_cpu_set_records(system_records)
    if len(system_records) == 0:
        warnings.warn(
            "WindowsのCPU Set情報が空のため、CPU affinityを変更しません。",
            stacklevel=2,
        )
        return None
    active_group_count = api.get_active_processor_group_count()
    process_groups = api.get_process_group_affinity()
    _validate_process_groups(active_group_count, process_groups)
    if active_group_count != 1 or len(process_groups) != 1:
        raise _WindowsHybridCpuDetectionUnavailable(
            "Windowsの複数Processor Groupには対応していません。"
        )
    efficiency_classes = {record.efficiency_class for record in system_records}
    if len(efficiency_classes) <= 1:
        return None
    p_efficiency_class = max(efficiency_classes)
    process_mask, system_mask = api.get_process_affinity_mask()
    _validate_process_system_masks(process_mask, system_mask)
    process_records = _filter_process_records(records, process_mask, process_groups)
    process_efficiency_classes = {record.efficiency_class for record in process_records}
    if (
        p_efficiency_class not in process_efficiency_classes
        or len(process_efficiency_classes - {p_efficiency_class}) == 0
    ):
        return None
    topology = _topology_from_records(process_records, p_efficiency_class)
    return topology


def detect_windows_hybrid_cpu_topology() -> HybridCpuTopology | None:
    """WindowsのCPU Set情報からP/Eコア構成を検出する。"""
    try:
        return _detect_windows_hybrid_cpu_topology()
    except _WindowsHybridCpuDetectionUnavailable:
        warnings.warn(
            "WindowsのP/Eコア情報を取得できないため、CPU affinityを変更しません。",
            stacklevel=2,
        )
        return None
    except OSError as error:
        if _is_windows_hybrid_detection_unavailable_error(error):
            warnings.warn(
                "WindowsのP/Eコア情報を取得できないため、CPU affinityを変更しません。",
                stacklevel=2,
            )
            return None
        raise


def _logical_processor_indices_to_mask(
    logical_processor_indices: tuple[int, ...],
) -> int:
    mask = 0
    for logical_processor_index in logical_processor_indices:
        if (
            isinstance(logical_processor_index, bool)
            or not isinstance(logical_processor_index, int)
            or not 0 <= logical_processor_index < _MAX_PROCESSOR_GROUP_SIZE
        ):
            raise ValueError("Windowsの論理プロセッサ番号が不正です。")
        bit = 1 << logical_processor_index
        if mask & bit:
            raise ValueError("Windowsの論理プロセッサ番号に重複があります。")
        mask |= bit
    if mask == 0:
        raise ValueError("Windowsの対象論理プロセッサが空です。")
    return mask


def _check_process_mask_for_target(
    api: _WindowsApi,
    target_mask: int,
) -> int:
    active_group_count = api.get_active_processor_group_count()
    process_groups = api.get_process_group_affinity()
    _validate_single_processor_group(
        active_group_count,
        process_groups,
        "WindowsのCPU affinity適用は単一のProcessor Groupに限定されています。",
    )
    process_mask, system_mask = api.get_process_affinity_mask()
    _validate_process_system_masks(process_mask, system_mask)
    if (target_mask & ~process_mask) != 0:
        raise ValueError("Windowsの対象CPU affinityが現在のプロセス制限を広げます。")
    return process_mask


def _validate_single_processor_group(
    active_group_count: int,
    process_groups: tuple[int, ...],
    message: str,
) -> None:
    if active_group_count != 1 or len(process_groups) != 1:
        raise RuntimeError(message)
    if not 0 <= process_groups[0] < active_group_count:
        raise RuntimeError("WindowsのプロセスProcessor Group番号が不正です。")


def _validate_process_system_masks(process_mask: int, system_mask: int) -> None:
    if process_mask == 0 or system_mask == 0 or (process_mask & ~system_mask) != 0:
        raise ValueError("Windowsのプロセスhard affinity maskが不正です。")


def _validate_windows_plan_invariants(plan: WindowsCpuExecutionPlan) -> None:
    if (
        isinstance(plan.cpu_num_threads, bool)
        or not isinstance(plan.cpu_num_threads, int)
        or plan.cpu_num_threads < 1
    ):
        raise ValueError("WindowsのCPUスレッド数は1以上の整数で指定してください。")
    try:
        unique_indices = set(plan.logical_processor_indices)
    except TypeError as error:
        raise ValueError("Windowsの論理プロセッサ番号が不正です。") from error
    if len(unique_indices) != len(plan.logical_processor_indices):
        raise ValueError("Windowsの論理プロセッサ番号に重複があります。")
    if len(unique_indices) <= plan.cpu_num_threads:
        raise ValueError(
            "Windowsの対象論理プロセッサ数はCPUスレッド数より多い必要があります。"
        )


def _rollback_process_mask(
    api: _WindowsApi,
    previous_mask: int,
    original_error: Exception,
) -> None:
    try:
        api.set_process_affinity_mask(previous_mask)
        restored_mask, restored_system_mask = api.get_process_affinity_mask()
        _validate_process_system_masks(restored_mask, restored_system_mask)
        if restored_mask != previous_mask:
            raise RuntimeError("Windowsのプロセスhard affinity maskを復元できません。")
    except Exception as rollback_error:
        raise RuntimeError(
            "WindowsのCPU affinity適用に失敗し、ロールバック後の状態を確認できません。"
            f" 元のエラー: {original_error}"
        ) from rollback_error


def apply_windows_cpu_execution_plan(plan: WindowsCpuExecutionPlan) -> None:
    """WindowsのCPU実行計画をプロセスhard affinityへ適用する。"""
    _validate_windows_plan_invariants(plan)
    target_mask = _logical_processor_indices_to_mask(plan.logical_processor_indices)
    api = _get_windows_api()
    previous_mask = _check_process_mask_for_target(api, target_mask)
    try:
        api.set_process_affinity_mask(target_mask)
        current_mask, current_system_mask = api.get_process_affinity_mask()
        _validate_process_system_masks(current_mask, current_system_mask)
        if current_mask != target_mask:
            raise RuntimeError(
                "Windowsのプロセスhard affinity maskが計画と一致しません。"
            )
    except Exception as error:
        _rollback_process_mask(api, previous_mask, error)
        raise


def validate_windows_cpu_execution_plan(plan: WindowsCpuExecutionPlan) -> None:
    """Windowsのプロセスhard affinityがCPU実行計画と一致することを検証する。"""
    _validate_windows_plan_invariants(plan)
    target_mask = _logical_processor_indices_to_mask(plan.logical_processor_indices)
    api = _get_windows_api()
    current_mask = _check_process_mask_for_target(api, target_mask)
    if current_mask != target_mask:
        raise RuntimeError(
            "Windowsのプロセスhard affinity maskがCPU実行計画と一致しません。"
        )
