"""WindowsのハイブリッドCPU構成を取得し、CPU affinityを操作する。"""

import ctypes
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, cast

_ERROR_INSUFFICIENT_BUFFER = 122
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
            self._get_current_process: Any = kernel32.GetCurrentProcess
            self._get_system_cpu_set_information: Any = (
                kernel32.GetSystemCpuSetInformation
            )
            self._get_process_affinity_mask: Any = kernel32.GetProcessAffinityMask
            self._set_process_affinity_mask: Any = kernel32.SetProcessAffinityMask
            self._get_active_processor_group_count: Any = (
                kernel32.GetActiveProcessorGroupCount
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

    @staticmethod
    def _last_error_code() -> int:
        error_function_name = "get_last_error"
        get_last_error = cast(Callable[[], int], getattr(ctypes, error_function_name))
        return get_last_error()

    @classmethod
    def _last_error(cls) -> OSError:
        return OSError(cls._last_error_code())

    def _current_process(self) -> _HANDLE:
        return cast(_HANDLE, self._get_current_process())

    def get_system_cpu_set_information(self) -> bytes:
        """CPU Set情報を可変長レコード列として取得する。"""
        required_length = _DWORD()
        result = self._get_system_cpu_set_information(
            None,
            0,
            ctypes.byref(required_length),
            self._current_process(),
            0,
        )
        if not result and self._last_error_code() != _ERROR_INSUFFICIENT_BUFFER:
            raise self._last_error()
        if required_length.value == 0:
            return b""

        buffer = (ctypes.c_ubyte * required_length.value)()
        returned_length = _DWORD()
        result = self._get_system_cpu_set_information(
            ctypes.cast(buffer, ctypes.c_void_p),
            required_length.value,
            ctypes.byref(returned_length),
            self._current_process(),
            0,
        )
        if not result:
            raise self._last_error()
        if returned_length.value > required_length.value:
            raise ValueError("WindowsのCPU Set情報の長さが不正です。")
        return bytes(buffer[: returned_length.value])

    def get_process_affinity_mask(self) -> tuple[int, int]:
        """起動時の現在プロセスとシステムのhard affinity maskを取得する。"""
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
        return int(self._get_active_processor_group_count())


def _get_windows_api() -> _WindowsApi:
    return _WindowsApi()


def _parse_cpu_set_records(buffer: bytes) -> tuple[_WindowsCpuSetRecord, ...]:
    records: list[_WindowsCpuSetRecord] = []
    offset = 0
    header_size = ctypes.sizeof(_SystemCpuSetInformationHeader)
    minimum_size = ctypes.sizeof(_SystemCpuSetInformation)
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
                    int(cpu_set.Group),
                    int(cpu_set.LogicalProcessorIndex),
                    int(cpu_set.EfficiencyClass),
                    bool(cpu_set.Flags & 0b10),
                    bool(cpu_set.Flags & 0b100),
                )
            )
        offset += size

    return tuple(records)


def _available_records(
    records: tuple[_WindowsCpuSetRecord, ...],
    process_mask: int,
    system_mask: int,
) -> tuple[_WindowsCpuSetRecord, ...]:
    allowed_mask = process_mask & system_mask
    return tuple(
        record
        for record in records
        if not record.allocated or record.allocated_to_target_process
        if record.group == 0
        and record.logical_processor_index < _MAX_PROCESSOR_GROUP_SIZE
        and allowed_mask & (1 << record.logical_processor_index)
    )


def configure_windows_cpu_execution(cpu_num_threads: int) -> None:
    """利用可能な論理PコアへWindowsのプロセスを一度制限する。"""
    try:
        api = _get_windows_api()
    except _WindowsHybridCpuDetectionUnavailable:
        return

    if api.get_active_processor_group_count() != 1:
        return

    records = _parse_cpu_set_records(api.get_system_cpu_set_information())
    if len(records) == 0:
        return

    process_mask, system_mask = api.get_process_affinity_mask()
    records = _available_records(records, process_mask, system_mask)
    if len(records) == 0:
        return

    efficiency_classes = {record.efficiency_class for record in records}
    if len(efficiency_classes) <= 1:
        return
    p_efficiency_class = max(efficiency_classes)
    p_records = tuple(
        record for record in records if record.efficiency_class == p_efficiency_class
    )
    if len(p_records) <= cpu_num_threads:
        return

    target_mask = 0
    for record in p_records:
        target_mask |= 1 << record.logical_processor_index
    if target_mask == 0:
        return
    api.set_process_affinity_mask(target_mask)
