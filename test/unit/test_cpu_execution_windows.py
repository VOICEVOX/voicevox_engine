"""`cpu_execution_windows.py` のテスト"""

from __future__ import annotations

import ctypes
from unittest.mock import patch

import pytest

from voicevox_engine.core import cpu_execution_windows as windows


def _record(
    cpu_set_id: int,
    group: int,
    logical_processor_index: int,
    efficiency_class: int,
    flags: int = 0,
    size: int | None = None,
    record_type: int = 0,
) -> bytes:
    record = windows._SystemCpuSetInformation()
    record.Size = size or ctypes.sizeof(windows._SystemCpuSetInformation)
    record.Type = record_type
    record.CpuSet.Id = cpu_set_id
    record.CpuSet.Group = group
    record.CpuSet.LogicalProcessorIndex = logical_processor_index
    record.CpuSet.EfficiencyClass = efficiency_class
    record.CpuSet.Flags = flags
    result = bytearray(bytes(record))
    result.extend(b"x" * (record.Size - len(result)))
    return bytes(result)


def _hybrid_records() -> bytes:
    return b"".join(
        [
            _record(900, 0, 1, 20),
            _record(100, 0, 4, 20),
            _record(7, 0, 7, 10),
            _record(8, 0, 9, 10),
        ]
    )


class _FakeWindowsApi:
    def __init__(
        self,
        records: bytes,
        process_mask: int,
        active_group_count: int = 1,
    ) -> None:
        self.records = records
        self.process_mask = process_mask
        self.active_group_count = active_group_count
        self.active_group_calls = 0
        self.set_masks: list[int] = []
        self.process_mask_calls = 0

    def get_system_cpu_set_information(self) -> bytes:
        return self.records

    def get_process_affinity_mask(self) -> int:
        self.process_mask_calls += 1
        return self.process_mask

    def set_process_affinity_mask(self, mask: int) -> None:
        self.set_masks.append(mask)

    def get_active_processor_group_count(self) -> int:
        self.active_group_calls += 1
        return self.active_group_count


def test_parse_cpu_set_records_uses_size_and_logical_index() -> None:
    """CPU Set IDではなく論理プロセッサ番号をSize走査で取得する。"""
    records = _record(
        1000, 0, 3, 20, size=ctypes.sizeof(windows._SystemCpuSetInformation) + 8
    )
    records += _record(2000, 0, 5, 10, record_type=99)

    parsed = windows._parse_cpu_set_records(records)

    assert len(parsed) == 1
    assert parsed[0].logical_processor_index == 3
    assert parsed[0].efficiency_class == 20


@pytest.mark.parametrize("size", [0, 7, 31])
def test_parse_cpu_set_records_rejects_invalid_size(size: int) -> None:
    """不正なレコードSizeを拒否する。"""
    broken = size.to_bytes(4, "little") + b"\x00" * 4
    with pytest.raises(ValueError, match="長さ|Buffer"):
        windows._parse_cpu_set_records(broken)


def test_configure_windows_cpu_execution_uses_all_allowed_p_cores_once() -> None:
    """P>Nなら割り当てとprocess maskに残る全Pコアを一度設定する。"""
    records = _hybrid_records()
    records += _record(700, 0, 13, 20, flags=0b10)
    records += _record(800, 0, 15, 20, flags=0b10 | 0b100)
    api = _FakeWindowsApi(records, (1 << 1) | (1 << 4) | (1 << 7) | (1 << 15))

    with patch.object(windows, "_WindowsApi", return_value=api):
        windows.configure_windows_cpu_execution(1)

    assert api.set_masks == [(1 << 1) | (1 << 4) | (1 << 15)]
    assert api.active_group_calls == 1
    assert api.process_mask_calls == 1


@pytest.mark.parametrize("cpu_num_threads", [2, 3])
def test_configure_windows_cpu_execution_does_not_set_when_p_is_not_larger(
    cpu_num_threads: int,
) -> None:
    """P数がN以下ならプロセスmaskを設定しない。"""
    api = _FakeWindowsApi(_hybrid_records(), (1 << 16) - 1)

    with patch.object(windows, "_WindowsApi", return_value=api):
        windows.configure_windows_cpu_execution(cpu_num_threads)

    assert api.set_masks == []


def test_configure_windows_cpu_execution_does_not_set_for_one_efficiency_class() -> (
    None
):
    """EfficiencyClassが一種類ならP/Eとして扱わない。"""
    records = _record(100, 0, 1, 20) + _record(200, 0, 2, 20)
    api = _FakeWindowsApi(records, 0b110)

    with patch.object(windows, "_WindowsApi", return_value=api):
        windows.configure_windows_cpu_execution(1)

    assert api.set_masks == []


def test_configure_windows_cpu_execution_does_not_set_for_multiple_groups() -> None:
    """Processor Groupが複数ならCPU affinityを変更しない。"""
    api = _FakeWindowsApi(
        _hybrid_records(),
        (1 << 16) - 1,
        active_group_count=2,
    )

    with patch.object(windows, "_WindowsApi", return_value=api):
        windows.configure_windows_cpu_execution(1)

    assert api.process_mask_calls == 0
    assert api.set_masks == []


def test_configure_windows_cpu_execution_rejects_zero_processor_groups() -> None:
    """Processor Group数0をAPI失敗として扱う。"""
    api = _FakeWindowsApi(_hybrid_records(), (1 << 16) - 1, active_group_count=0)

    with patch.object(windows, "_WindowsApi", return_value=api):
        with pytest.raises(OSError, match="Processor Group"):
            windows.configure_windows_cpu_execution(1)


def test_configure_windows_cpu_execution_propagates_process_mask_error() -> None:
    """GetProcessAffinityMaskの失敗を伝播する。"""
    api = _FakeWindowsApi(_hybrid_records(), (1 << 16) - 1)
    error = OSError("process mask error")
    with patch.object(api, "get_process_affinity_mask", side_effect=error):
        with patch.object(windows, "_WindowsApi", return_value=api):
            with pytest.raises(OSError, match="process mask error"):
                windows.configure_windows_cpu_execution(1)


def test_configure_windows_cpu_execution_propagates_set_error() -> None:
    """SetProcessAffinityMaskの失敗を伝播する。"""
    api = _FakeWindowsApi(_hybrid_records(), (1 << 16) - 1)
    error = OSError("set mask error")
    with patch.object(api, "set_process_affinity_mask", side_effect=error):
        with patch.object(windows, "_WindowsApi", return_value=api):
            with pytest.raises(OSError, match="set mask error"):
                windows.configure_windows_cpu_execution(1)


def test_get_system_cpu_set_information_uses_two_stage_buffer() -> None:
    """GetSystemCpuSetInformationを容量取得と本取得の二段階で呼ぶ。"""
    api = object.__new__(windows._WindowsApi)
    calls: list[bool] = []

    def get_information(
        information: object,
        buffer_size: int,
        returned_length: ctypes._CArgObject,
        process: object,
        flags: int,
    ) -> int:
        del buffer_size, process, flags
        calls.append(information is None)
        pointer = ctypes.cast(returned_length, ctypes.POINTER(windows._DWORD))
        pointer.contents.value = 8
        return 0 if information is None else 1

    api._get_system_cpu_set_information = get_information
    with patch.object(
        windows._WindowsApi, "_current_process", return_value=windows._HANDLE(1)
    ):
        with patch.object(windows._WindowsApi, "_last_error_code", return_value=122):
            assert api.get_system_cpu_set_information() == bytes(8)
    assert calls == [True, False]


def test_get_system_cpu_set_information_propagates_bool_failure() -> None:
    """第一段階のBOOL失敗をctypes.WinErrorで例外化して伝播する。"""
    api = object.__new__(windows._WindowsApi)

    def get_information(
        information: object,
        buffer_size: int,
        returned_length: ctypes._CArgObject,
        process: object,
        flags: int,
    ) -> int:
        del information, buffer_size, returned_length, process, flags
        return 0

    api._get_system_cpu_set_information = get_information
    with patch.object(
        windows._WindowsApi, "_current_process", return_value=windows._HANDLE(1)
    ):
        with patch.object(windows._WindowsApi, "_last_error_code", return_value=5):
            with patch.object(
                ctypes, "WinError", return_value=OSError(5), create=True
            ) as win_error:
                with pytest.raises(OSError, match="5"):
                    api.get_system_cpu_set_information()
    win_error.assert_called_once_with()
