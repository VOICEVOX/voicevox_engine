"""`cpu_execution_windows.py` のテスト"""

from __future__ import annotations

import ctypes
import warnings
from unittest.mock import patch

import pytest

from voicevox_engine.core import cpu_execution_windows as windows
from voicevox_engine.core.cpu_execution import WindowsCpuExecutionPlan


class _WindowsApiError(OSError):
    winerror: int


def _os_error(errno_value: int, winerror: int | None = None) -> OSError:
    error = _WindowsApiError(errno_value, "Windows API error")
    if winerror is not None:
        error.winerror = winerror
    return error


class _FakeWindowsApi:
    def __init__(
        self,
        records: bytes,
        process_mask: int,
        system_mask: int,
        process_groups: tuple[int, ...],
        active_group_count: int,
    ) -> None:
        self.records = records
        self.process_mask = process_mask
        self.system_mask = system_mask
        self.process_groups = process_groups
        self.active_group_count = active_group_count
        self.set_masks: list[int] = []
        self.fail_set = False
        self.report_masks: list[int] = []

    def get_system_cpu_set_information(self) -> bytes:
        return self.records

    def get_process_affinity_mask(self) -> tuple[int, int]:
        if len(self.report_masks) != 0:
            report_mask = self.report_masks.pop(0)
            return report_mask, self.system_mask
        return self.process_mask, self.system_mask

    def set_process_affinity_mask(self, mask: int) -> None:
        self.set_masks.append(mask)
        if self.fail_set:
            raise OSError("mask設定に失敗しました")
        self.process_mask = mask

    def get_process_group_affinity(self) -> tuple[int, ...]:
        return self.process_groups

    def get_active_processor_group_count(self) -> int:
        return self.active_group_count


class _MaskAccessForbiddenWindowsApi(_FakeWindowsApi):
    def get_process_affinity_mask(self) -> tuple[int, int]:
        raise AssertionError("GetProcessAffinityMaskは呼び出されません")


def _record(
    cpu_set_id: int,
    group: int,
    logical_processor_index: int,
    core_index: int,
    efficiency_class: int,
    flags: int,
    size: int | None,
    record_type: int,
) -> bytes:
    record = windows._SystemCpuSetInformation()
    record.Size = size or ctypes.sizeof(windows._SystemCpuSetInformation)
    record.Type = record_type
    record.CpuSet.Id = cpu_set_id
    record.CpuSet.Group = group
    record.CpuSet.LogicalProcessorIndex = logical_processor_index
    record.CpuSet.CoreIndex = core_index
    record.CpuSet.EfficiencyClass = efficiency_class
    record.CpuSet.Flags = flags
    result = bytearray(bytes(record))
    result.extend(b"x" * (record.Size - len(result)))
    return bytes(result)


def _hybrid_records() -> bytes:
    return b"".join(
        [
            _record(100, 0, 1, 10, 20, 0, None, 0),
            _record(500, 0, 4, 10, 20, 0, None, 0),
            _record(7, 0, 7, 20, 15, 0, None, 0),
            _record(900, 0, 9, 21, 10, 0, None, 0),
            _record(901, 0, 11, 21, 10, 0, None, 0),
        ]
    )


def test_parse_cpu_set_records_uses_size_for_variable_records() -> None:
    """CPU Set情報をSizeで走査し、未知のレコード種別を飛ばせる。"""
    records = _record(100, 0, 3, 1, 20, 0, 40, 0) + _record(
        700,
        0,
        5,
        2,
        10,
        0,
        None,
        record_type=99,
    )

    parsed = windows._parse_cpu_set_records(records)

    assert [
        (record.cpu_set_id, record.logical_processor_index) for record in parsed
    ] == [(100, 3)]


def test_parse_cpu_set_records_skips_unknown_small_record() -> None:
    """CPU Set以外の最小ヘッダだけのレコードを飛ばす。"""
    unknown_record = (8).to_bytes(4, "little") + (99).to_bytes(4, "little")

    assert windows._parse_cpu_set_records(unknown_record) == ()


@pytest.mark.parametrize("size", [0, 7, 31, 33])
def test_parse_cpu_set_records_rejects_broken_size(size: int) -> None:
    """CPU Set情報の不正なSizeを拒否する。"""
    if size == 33:
        broken = _record(1, 0, 0, 0, 1, 0, 32, 0) + b"x"
    else:
        broken = size.to_bytes(4, "little") + b"\x00" * 4

    with pytest.raises(ValueError, match="長さ|ヘッダー"):
        windows._parse_cpu_set_records(broken)


def test_detect_uses_logical_processor_index_not_cpu_set_id() -> None:
    """CPU Set IDではなくGroup内の論理プロセッサ番号で分類する。"""
    api = _FakeWindowsApi(
        _hybrid_records(),
        (1 << 1) | (1 << 4) | (1 << 7) | (1 << 9) | (1 << 11),
        (1 << 12) - 1,
        (0,),
        1,
    )

    with patch.object(windows, "_get_windows_api", return_value=api):
        topology = windows.detect_windows_hybrid_cpu_topology()

    assert topology is not None
    assert topology.p_logical_cpu_ids == (1, 4)
    assert topology.e_logical_cpu_ids == (7, 9, 11)


def test_detect_excludes_foreign_allocated_cpu_set_but_keeps_parked() -> None:
    """他プロセスに割り当て済みのCPU Setを除外し、Parkedは除外しない。"""
    records = _hybrid_records() + _record(1000, 0, 13, 30, 5, 0b10, None, 0)
    api = _FakeWindowsApi(
        records,
        (1 << 16) - 1,
        (1 << 16) - 1,
        (0,),
        1,
    )
    parked = _record(1001, 0, 15, 31, 20, 0b1, None, 0)
    api.records = records + parked

    with patch.object(windows, "_get_windows_api", return_value=api):
        topology = windows.detect_windows_hybrid_cpu_topology()

    assert topology is not None
    assert 15 in topology.p_logical_cpu_ids
    assert 13 not in topology.e_logical_cpu_ids


def test_detect_rejects_duplicate_allocated_cpu_set_id() -> None:
    """除外対象でも重複したCPU Set IDを拒否する。"""
    records = _record(1, 0, 0, 0, 20, 0b10, None, 0) + _record(
        1, 0, 1, 1, 10, 0b10, None, 0
    )
    api = _FakeWindowsApi(records, 0b111111, 0b111111, (0,), 1)

    with patch.object(windows, "_get_windows_api", return_value=api):
        with pytest.raises(ValueError, match="IDに重複"):
            windows.detect_windows_hybrid_cpu_topology()


def test_detect_warns_when_cpu_set_api_is_unavailable() -> None:
    """CPU Set APIがない場合は警告してlegacy扱いにする。"""
    error = windows._WindowsHybridCpuDetectionUnavailable("利用できません")
    with patch.object(windows, "_get_windows_api", side_effect=error):
        with pytest.warns(UserWarning, match="取得できない"):
            assert windows.detect_windows_hybrid_cpu_topology() is None


def test_windows_api_missing_required_export_raises_dedicated_error() -> None:
    """必須APIのexport欠如を検出不能専用例外へ変換する。"""
    with patch.object(ctypes, "WinDLL", return_value=object(), create=True):
        with patch.object(
            windows,
            "_get_library_function",
            side_effect=AttributeError("exportがありません"),
        ):
            with pytest.raises(windows._WindowsHybridCpuDetectionUnavailable):
                windows._WindowsApi()


def test_windows_api_kernel32_load_error_is_not_converted() -> None:
    """kernel32の読み込みエラーを検出不能へ変換しない。"""
    error = _os_error(5)
    with patch.object(ctypes, "WinDLL", side_effect=error, create=True):
        with pytest.raises(OSError, match="Windows API error"):
            windows._WindowsApi()


@pytest.mark.parametrize(
    ("errno_value", "winerror"),
    [(5, 50), (5, 120), (50, None), (120, None)],
)
def test_detect_downgrades_known_unsupported_api_errors(
    errno_value: int,
    winerror: int | None,
) -> None:
    """既知の未対応APIエラーを警告して検出不能にする。"""
    error = _os_error(errno_value, winerror)
    with patch.object(windows, "_get_windows_api", side_effect=error):
        with pytest.warns(UserWarning, match="取得できない"):
            assert windows.detect_windows_hybrid_cpu_topology() is None


@pytest.mark.parametrize(
    ("errno_value", "winerror"),
    [(5, None), (50, 5), (123, None)],
)
def test_detect_propagates_other_api_errors(
    errno_value: int,
    winerror: int | None,
) -> None:
    """未知またはアクセス拒否のAPIエラーを伝播する。"""
    error = _os_error(errno_value, winerror)
    with patch.object(windows, "_get_windows_api", side_effect=error):
        with pytest.raises(OSError, match="Windows API error"):
            windows.detect_windows_hybrid_cpu_topology()


def test_detect_returns_none_for_homogeneous_efficiency_class() -> None:
    """EfficiencyClassが一種類ならhybridとして扱わない。"""
    records = _record(1, 0, 1, 0, 20, 0, None, 0) + _record(2, 0, 2, 1, 20, 0, None, 0)
    api = _FakeWindowsApi(records, 0b110, 0b111111, (0,), 1)

    with patch.object(windows, "_get_windows_api", return_value=api):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            topology = windows.detect_windows_hybrid_cpu_topology()

    assert topology is None
    assert caught == []


def test_detect_warns_for_empty_system_records() -> None:
    """空のCPU Set情報を警告して検出不能にする。"""
    api = _FakeWindowsApi(b"", 0b1, 0b1, (0,), 1)

    with patch.object(windows, "_get_windows_api", return_value=api):
        with pytest.warns(UserWarning, match="空"):
            assert windows.detect_windows_hybrid_cpu_topology() is None


def test_detect_returns_none_for_multiple_processor_groups() -> None:
    """P/E混在時の複数Processor Groupをaffinityなしにする。"""
    api = _MaskAccessForbiddenWindowsApi(
        _hybrid_records(),
        (1 << 12) - 1,
        (1 << 12) - 1,
        (0, 1),
        2,
    )

    with patch.object(windows, "_get_windows_api", return_value=api):
        with pytest.warns(UserWarning, match="取得できない"):
            assert windows.detect_windows_hybrid_cpu_topology() is None


def test_detect_propagates_mask_error_for_single_processor_group() -> None:
    """単一Processor Groupのmask取得エラーを検出不能へ変換しない。"""
    api = _FakeWindowsApi(
        _hybrid_records(),
        (1 << 12) - 1,
        (1 << 12) - 1,
        (0,),
        1,
    )
    error = _os_error(5)

    with patch.object(api, "get_process_affinity_mask", side_effect=error):
        with patch.object(windows, "_get_windows_api", return_value=api):
            with pytest.raises(OSError, match="Windows API error"):
                windows.detect_windows_hybrid_cpu_topology()


def test_detect_rejects_invalid_process_group() -> None:
    """Windowsの不正なプロセスProcessor Group番号を拒否する。"""
    api = _FakeWindowsApi(
        _hybrid_records(),
        (1 << 12) - 1,
        (1 << 12) - 1,
        (1,),
        1,
    )

    with patch.object(windows, "_get_windows_api", return_value=api):
        with pytest.raises(RuntimeError, match="番号"):
            windows.detect_windows_hybrid_cpu_topology()


def test_detect_does_not_treat_allowed_e_cores_as_p_cores() -> None:
    """許可範囲に真のPコアがなければP/E検出不能にする。"""
    api = _FakeWindowsApi(
        _hybrid_records(),
        (1 << 7) | (1 << 9) | (1 << 11),
        (1 << 12) - 1,
        (0,),
        1,
    )

    with patch.object(windows, "_get_windows_api", return_value=api):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            assert windows.detect_windows_hybrid_cpu_topology() is None
    assert caught == []


@pytest.mark.parametrize("process_groups", [(), (0, 0), (2,)])
def test_detect_rejects_invalid_process_groups(
    process_groups: tuple[int, ...],
) -> None:
    """空、重複、範囲外のProcessor Groupを拒否する。"""
    api = _FakeWindowsApi(
        _hybrid_records(),
        (1 << 12) - 1,
        (1 << 12) - 1,
        process_groups,
        2,
    )

    with patch.object(windows, "_get_windows_api", return_value=api):
        with pytest.raises((ValueError, RuntimeError)):
            windows.detect_windows_hybrid_cpu_topology()


def test_detect_intersects_current_process_mask() -> None:
    """現在のhard maskから外れたCPU Setを分類対象にしない。"""
    api = _FakeWindowsApi(
        _hybrid_records(),
        (1 << 1) | (1 << 4),
        (1 << 12) - 1,
        (0,),
        1,
    )

    with patch.object(windows, "_get_windows_api", return_value=api):
        topology = windows.detect_windows_hybrid_cpu_topology()

    assert topology is None


def test_apply_builds_mask_from_logical_processor_indices() -> None:
    """Windowsの適用がCPU Set IDではなく論理プロセッサ番号をmaskへ変換する。"""
    api = _FakeWindowsApi(b"", (1 << 1) | (1 << 3), 0b1111, (0,), 1)
    plan = WindowsCpuExecutionPlan(1, (1, 3))

    with patch.object(windows, "_get_windows_api", return_value=api):
        windows.apply_windows_cpu_execution_plan(plan)

    assert api.set_masks == [(1 << 1) | (1 << 3)]


def test_apply_allows_affinity_target_with_more_cpus_than_threads() -> None:
    """Windowsの適用がNより多いP論理CPU集合を受け入れる。"""
    api = _FakeWindowsApi(b"", (1 << 1) | (1 << 3) | (1 << 5), 0b111111, (0,), 1)
    plan = WindowsCpuExecutionPlan(2, (1, 3, 5))

    with patch.object(windows, "_get_windows_api", return_value=api):
        windows.apply_windows_cpu_execution_plan(plan)

    assert api.set_masks == [(1 << 1) | (1 << 3) | (1 << 5)]


def test_apply_rejects_target_that_expands_existing_mask() -> None:
    """現在のhard maskを広げる計画を拒否する。"""
    api = _FakeWindowsApi(b"", 0b0011, 0b1111, (0,), 1)
    plan = WindowsCpuExecutionPlan(1, (0, 2))

    with patch.object(windows, "_get_windows_api", return_value=api):
        with pytest.raises(ValueError, match="広げます"):
            windows.apply_windows_cpu_execution_plan(plan)

    assert api.set_masks == []


def test_apply_rejects_invalid_process_group() -> None:
    """単一Group環境でも不正なプロセスGroup番号を拒否する。"""
    api = _FakeWindowsApi(
        b"",
        0b0011,
        0b1111,
        (1,),
        1,
    )
    plan = WindowsCpuExecutionPlan(1, (0, 1))

    with patch.object(windows, "_get_windows_api", return_value=api):
        with pytest.raises(RuntimeError, match="Group"):
            windows.apply_windows_cpu_execution_plan(plan)


def test_apply_rejects_plan_invariant_before_api_access() -> None:
    """重複した論理プロセッサを持つ計画をAPIアクセス前に拒否する。"""
    plan = WindowsCpuExecutionPlan(2, (0, 0))

    with patch.object(
        windows,
        "_get_windows_api",
        side_effect=AssertionError("APIは呼び出されません"),
    ):
        with pytest.raises(ValueError, match="重複"):
            windows.apply_windows_cpu_execution_plan(plan)


def test_validate_rejects_plan_invariant_before_api_access() -> None:
    """Windowsの検証が不変条件をAPIアクセス前に確認する。"""
    plan = WindowsCpuExecutionPlan(2, (0, 0))

    with patch.object(
        windows,
        "_get_windows_api",
        side_effect=AssertionError("APIは呼び出されません"),
    ):
        with pytest.raises(ValueError, match="重複"):
            windows.validate_windows_cpu_execution_plan(plan)


def test_apply_rejects_target_not_larger_than_threads_before_api_access() -> None:
    """対象論理CPU数がN以下の計画をAPIアクセス前に拒否する。"""
    plan = WindowsCpuExecutionPlan(2, (0, 1))

    with patch.object(
        windows,
        "_get_windows_api",
        side_effect=AssertionError("APIは呼び出されません"),
    ):
        with pytest.raises(ValueError, match="より多い"):
            windows.apply_windows_cpu_execution_plan(plan)


def test_apply_rolls_back_when_postcondition_does_not_match() -> None:
    """適用後のmask不一致時に元のmaskへ戻す。"""
    api = _FakeWindowsApi(b"", 0b1111, 0b1111, (0,), 1)
    api.report_masks = [0b1111, 0b1000]
    plan = WindowsCpuExecutionPlan(1, (0, 1))

    with patch.object(windows, "_get_windows_api", return_value=api):
        with pytest.raises(RuntimeError, match="一致しません"):
            windows.apply_windows_cpu_execution_plan(plan)

    assert api.set_masks == [0b0011, 0b1111]


def test_apply_reports_rollback_failure() -> None:
    """ロールバック失敗時に状態不定のエラーを返す。"""
    api = _FakeWindowsApi(b"", 0b1111, 0b1111, (0,), 1)
    api.fail_set = True
    plan = WindowsCpuExecutionPlan(1, (0, 1))

    with patch.object(windows, "_get_windows_api", return_value=api):
        with pytest.raises(RuntimeError, match="ロールバック"):
            windows.apply_windows_cpu_execution_plan(plan)


def test_validate_requires_exact_process_mask() -> None:
    """Windowsの検証が計画集合との完全一致を要求する。"""
    api = _FakeWindowsApi(b"", 0b0011, 0b1111, (0,), 1)
    plan = WindowsCpuExecutionPlan(1, (0, 1))

    with patch.object(windows, "_get_windows_api", return_value=api):
        windows.validate_windows_cpu_execution_plan(plan)

    api.process_mask = 0b0111
    with patch.object(windows, "_get_windows_api", return_value=api):
        with pytest.raises(RuntimeError, match="一致しません"):
            windows.validate_windows_cpu_execution_plan(plan)


def test_import_is_possible_without_windll() -> None:
    """WindowsモジュールのimportがWinDLLのない環境でも成立する。"""
    assert hasattr(windows, "detect_windows_hybrid_cpu_topology")


def test_get_system_cpu_set_information_retries_second_insufficient_buffer() -> None:
    """二段階取得の二回目だけ容量不足なら再取得する。"""
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
        is_query = information is None
        calls.append(is_query)
        returned_length_pointer = ctypes.cast(
            returned_length,
            ctypes.POINTER(windows._DWORD),
        )
        returned_length_pointer.contents.value = 32
        if is_query:
            return 0
        if calls.count(False) == 1:
            return 0
        return 1

    api._get_system_cpu_set_information = get_information
    with patch.object(
        windows._WindowsApi,
        "_current_process",
        return_value=windows._HANDLE(1),
    ):
        with patch.object(
            windows._WindowsApi,
            "_last_error_code",
            side_effect=[122, 122, 122],
        ):
            assert api.get_system_cpu_set_information() == bytes(32)
    assert calls == [True, False, True, False]


def test_get_system_cpu_set_information_raises_after_three_unstable_retries() -> None:
    """三回連続の容量不足を検出不能専用例外へ変換する。"""
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
        returned_length_pointer = ctypes.cast(
            returned_length,
            ctypes.POINTER(windows._DWORD),
        )
        returned_length_pointer.contents.value = 32
        return 0

    api._get_system_cpu_set_information = get_information
    with patch.object(
        windows._WindowsApi,
        "_current_process",
        return_value=windows._HANDLE(1),
    ):
        with patch.object(
            windows._WindowsApi,
            "_last_error_code",
            side_effect=[122] * 6,
        ):
            with pytest.raises(windows._WindowsHybridCpuDetectionUnavailable):
                api.get_system_cpu_set_information()
    assert calls == [True, False, True, False, True, False]


@pytest.mark.parametrize("returned_length", [0, 33])
def test_get_system_cpu_set_information_rejects_malformed_size(
    returned_length: int,
) -> None:
    """CPU Set情報のサイズ0または返却長超過を拒否する。"""
    api = object.__new__(windows._WindowsApi)

    def get_information(
        information: object,
        buffer_size: int,
        returned_length_pointer: ctypes._CArgObject,
        process: object,
        flags: int,
    ) -> int:
        del buffer_size, process, flags
        pointer = ctypes.cast(
            returned_length_pointer,
            ctypes.POINTER(windows._DWORD),
        )
        if information is None:
            pointer.contents.value = 32
        else:
            pointer.contents.value = returned_length
        return 1

    api._get_system_cpu_set_information = get_information
    with patch.object(
        windows._WindowsApi,
        "_current_process",
        return_value=windows._HANDLE(1),
    ):
        with pytest.raises(ValueError, match="長さ"):
            api.get_system_cpu_set_information()


def test_get_system_cpu_set_information_rejects_zero_required_size() -> None:
    """CPU Set情報の要求サイズ0を拒否する。"""
    api = object.__new__(windows._WindowsApi)

    def get_information(
        information: object,
        buffer_size: int,
        returned_length_pointer: ctypes._CArgObject,
        process: object,
        flags: int,
    ) -> int:
        del information, buffer_size, process, flags
        pointer = ctypes.cast(
            returned_length_pointer,
            ctypes.POINTER(windows._DWORD),
        )
        pointer.contents.value = 0
        return 1

    api._get_system_cpu_set_information = get_information
    with patch.object(
        windows._WindowsApi,
        "_current_process",
        return_value=windows._HANDLE(1),
    ):
        with pytest.raises(ValueError, match="長さ"):
            api.get_system_cpu_set_information()
