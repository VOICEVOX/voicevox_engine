"""`cpu_execution_linux.py` のテスト"""

import errno
import os
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import pytest

from voicevox_engine.core import cpu_execution_linux as linux
from voicevox_engine.core.cpu_execution import LinuxCpuExecutionPlan


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("3", {3}),
        ("3-5", {3, 4, 5}),
        ("3,7-8,12", {3, 7, 8, 12}),
    ],
)
def test_parse_cpu_list(value: str, expected: set[int]) -> None:
    """LinuxのCPUリストの単一、範囲、非連続表記を解釈する。"""
    assert linux._parse_cpu_list(value) == expected


@pytest.mark.parametrize("value", ["", "3-2", "3,,4", "3-", "-3", "3-4-5"])
def test_parse_cpu_list_rejects_invalid(value: str) -> None:
    """Linuxの不正なCPUリストを拒否する。"""
    with pytest.raises(ValueError, match="形式|範囲|空"):
        linux._parse_cpu_list(value)


def test_parse_cpu_list_rejects_duplicate() -> None:
    """LinuxのCPUリストの重複を拒否する。"""
    with pytest.raises(ValueError, match="重複"):
        linux._parse_cpu_list("1-3,3")


class _FakeThreads:
    def __init__(self, thread_ids: tuple[int, ...], masks: dict[int, set[int]]) -> None:
        self.thread_ids = list(thread_ids)
        self.masks = {thread_id: frozenset(mask) for thread_id, mask in masks.items()}
        self.set_calls: list[tuple[int, frozenset[int]]] = []
        self.fail_after: int | None = None
        self.failed = False

    def list_ids(self) -> tuple[int, ...]:
        return tuple(self.thread_ids)

    def get(self, thread_id: int) -> frozenset[int]:
        if thread_id not in self.masks:
            raise OSError(errno.ESRCH, "スレッドが終了しました")
        return self.masks[thread_id]

    def set(self, thread_id: int, affinity: frozenset[int]) -> None:
        if (
            self.fail_after is not None
            and len(self.set_calls) >= self.fail_after
            and self.failed is False
        ):
            self.failed = True
            raise OSError(errno.EPERM, "affinity設定に失敗しました")
        self.set_calls.append((thread_id, affinity))
        self.masks[thread_id] = affinity


def _write_topology(
    root: Path,
    p_cpus: str,
    e_cpus: str,
    online: str,
) -> None:
    (root / "cpu_core").mkdir(parents=True)
    (root / "cpu_atom").mkdir(parents=True)
    (root / "system_cpu").mkdir(parents=True)
    (root / "cpu_core" / "cpus").write_text(p_cpus, encoding="ascii")
    (root / "cpu_atom" / "cpus").write_text(e_cpus, encoding="ascii")
    (root / "system_cpu" / "online").write_text(online, encoding="ascii")


def _patch_topology_paths(root: Path) -> ExitStack:
    patches = ExitStack()
    patches.enter_context(
        patch.object(linux, "_CPU_CORE_CPUS_PATH", root / "cpu_core" / "cpus")
    )
    patches.enter_context(
        patch.object(linux, "_CPU_ATOM_CPUS_PATH", root / "cpu_atom" / "cpus")
    )
    patches.enter_context(
        patch.object(linux, "_ONLINE_CPUS_PATH", root / "system_cpu" / "online")
    )
    return patches


def test_detect_linux_topology_intersects_online_and_all_thread_masks(
    tmp_path: Path,
) -> None:
    """Linuxの検出がonlineと全TID affinityの共通部分を使う。"""
    _write_topology(
        tmp_path,
        "0-3",
        "4-5",
        "0-5",
    )
    threads = _FakeThreads(
        (100, 101),
        {100: {0, 1, 2, 3, 4, 5}, 101: {0, 1, 2, 3, 4, 5}},
    )
    path_patches = _patch_topology_paths(tmp_path)
    with patch.object(linux, "_is_x86", return_value=True):
        with path_patches:
            with patch.object(linux, "_list_thread_ids", side_effect=threads.list_ids):
                with patch.object(
                    linux,
                    "_get_thread_affinity",
                    side_effect=threads.get,
                ):
                    topology = linux.detect_linux_hybrid_cpu_topology()

    assert topology is not None
    assert topology.p_logical_cpu_ids == (0, 1, 2, 3)
    assert topology.e_logical_cpu_ids == (4, 5)


def test_detect_retries_when_topology_changes_during_detection(
    tmp_path: Path,
) -> None:
    """Linuxの検出が構成変化を検出した場合に再試行する。"""
    _write_topology(
        tmp_path,
        "0-1",
        "2-3",
        "0-3",
    )
    threads = _FakeThreads((100,), {100: {0, 1, 2, 3}})
    path_patches = _patch_topology_paths(tmp_path)
    with patch.object(linux, "_is_x86", return_value=True):
        with path_patches:
            with patch.object(linux, "_list_thread_ids", side_effect=threads.list_ids):
                with patch.object(
                    linux, "_get_thread_affinity", side_effect=threads.get
                ):
                    with patch.object(
                        linux,
                        "_ensure_detection_state_is_stable",
                        side_effect=[linux._LinuxAffinityRace(), None],
                    ) as ensure_stable:
                        topology = linux.detect_linux_hybrid_cpu_topology()

    assert topology is not None
    assert ensure_stable.call_count == 2


def test_detect_returns_none_after_retries_when_topology_is_unstable() -> None:
    """Linuxの構成が安定しない場合は警告してaffinityなしにする。"""
    with patch.object(linux, "_is_x86", return_value=True):
        with patch.object(
            linux,
            "_detect_linux_hybrid_cpu_topology_once",
            side_effect=[linux._LinuxAffinityRace() for _ in range(linux._MAX_RETRIES)],
        ) as detect_once:
            with pytest.warns(UserWarning, match="安定しない"):
                assert linux.detect_linux_hybrid_cpu_topology() is None

    assert detect_once.call_count == linux._MAX_RETRIES


def test_detect_retries_hybrid_sysfs_loss_then_downgrades() -> None:
    """検出途中のP/E sysfs消失を再試行し、継続時は検出不能にする。"""
    with patch.object(linux, "_is_x86", return_value=True):
        with patch.object(
            linux,
            "_read_hybrid_cpu_list",
            side_effect=[
                {0},
                {1},
                linux._LinuxHybridCpuDetectionUnavailable(),
                linux._LinuxHybridCpuDetectionUnavailable(),
            ],
        ) as read_hybrid:
            with patch.object(
                linux,
                "_snapshot_detection_state",
                return_value=({0, 1}, {100: frozenset({0, 1})}),
            ):
                with pytest.warns(UserWarning, match="取得できない"):
                    assert linux.detect_linux_hybrid_cpu_topology() is None

    assert read_hybrid.call_count == 4


@pytest.mark.parametrize("error_number", [errno.ENOSYS, errno.EOPNOTSUPP])
def test_detect_downgrades_unavailable_sched_getaffinity(
    tmp_path: Path,
    error_number: int,
) -> None:
    """未実装のsched_getaffinityを警告して検出不能にする。"""
    _write_topology(tmp_path, "0", "1", "0-1")
    path_patches = _patch_topology_paths(tmp_path)
    with patch.object(linux, "_is_x86", return_value=True):
        with path_patches:
            with patch.object(linux, "_list_thread_ids", return_value=(100,)):
                with patch.object(
                    os,
                    "sched_getaffinity",
                    side_effect=OSError(error_number, "unsupported"),
                ):
                    with pytest.warns(UserWarning, match="取得できない"):
                        assert linux.detect_linux_hybrid_cpu_topology() is None


def test_detect_downgrades_when_sched_getaffinity_is_missing(tmp_path: Path) -> None:
    """sched_getaffinity属性がない場合を警告して検出不能にする。"""
    _write_topology(tmp_path, "0", "1", "0-1")
    path_patches = _patch_topology_paths(tmp_path)
    with patch.object(linux, "_is_x86", return_value=True):
        with path_patches:
            with patch.object(linux, "_list_thread_ids", return_value=(100,)):
                with patch.object(os, "sched_getaffinity", None):
                    with pytest.warns(UserWarning, match="取得できない"):
                        assert linux.detect_linux_hybrid_cpu_topology() is None


@pytest.mark.parametrize("error_number", [errno.EPERM, errno.EACCES, errno.EIO])
def test_detect_propagates_sched_getaffinity_errors(
    tmp_path: Path,
    error_number: int,
) -> None:
    """権限エラーやI/Oエラーのsched_getaffinityを伝播する。"""
    _write_topology(tmp_path, "0", "1", "0-1")
    path_patches = _patch_topology_paths(tmp_path)
    with patch.object(linux, "_is_x86", return_value=True):
        with path_patches:
            with patch.object(linux, "_list_thread_ids", return_value=(100,)):
                with patch.object(
                    os,
                    "sched_getaffinity",
                    side_effect=OSError(error_number, "failure"),
                ):
                    with pytest.raises(OSError, match="failure"):
                        linux.detect_linux_hybrid_cpu_topology()


def test_detect_returns_none_on_non_x86_without_reading_hybrid_sysfs(
    tmp_path: Path,
) -> None:
    """Linuxの非x86環境をlegacy扱いにする。"""
    path_patches = _patch_topology_paths(tmp_path)
    with patch.object(linux, "_is_x86", return_value=False):
        with path_patches:
            assert linux.detect_linux_hybrid_cpu_topology() is None


def test_detect_returns_none_when_both_hybrid_sysfs_files_are_missing(
    tmp_path: Path,
) -> None:
    """Linuxの両方のhybrid sysfsがない場合はlegacy扱いにする。"""
    path_patches = _patch_topology_paths(tmp_path)
    with patch.object(linux, "_is_x86", return_value=True):
        with path_patches:
            with pytest.warns(UserWarning, match="取得できない"):
                assert linux.detect_linux_hybrid_cpu_topology() is None


def test_detect_returns_none_for_only_one_hybrid_sysfs_file(tmp_path: Path) -> None:
    """Linuxのhybrid sysfsが片方だけの場合はaffinityなしにする。"""
    (tmp_path / "cpu_core").mkdir()
    (tmp_path / "cpu_core" / "cpus").write_text("0", encoding="ascii")
    path_patches = _patch_topology_paths(tmp_path)
    with patch.object(linux, "_is_x86", return_value=True):
        with path_patches:
            with pytest.warns(UserWarning, match="取得できない"):
                assert linux.detect_linux_hybrid_cpu_topology() is None


@pytest.mark.parametrize("empty_path", ["p", "e"])
def test_detect_warns_for_empty_hybrid_sysfs_file(
    tmp_path: Path,
    empty_path: str,
) -> None:
    """空のP/E sysfsを警告してlegacy扱いにする。"""
    _write_topology(
        tmp_path,
        "" if empty_path == "p" else "0",
        "" if empty_path == "e" else "1",
        "0-1",
    )
    path_patches = _patch_topology_paths(tmp_path)
    with patch.object(linux, "_is_x86", return_value=True):
        with path_patches:
            with pytest.warns(UserWarning, match="取得できない"):
                assert linux.detect_linux_hybrid_cpu_topology() is None


@pytest.mark.parametrize(
    "error",
    [
        PermissionError(errno.EPERM, "permission denied"),
        OSError(errno.EIO, "I/O error"),
    ],
)
def test_read_hybrid_cpu_list_propagates_non_detection_errors(
    tmp_path: Path,
    error: OSError,
) -> None:
    """P/E sysfsの権限エラーやI/Oエラーを伝播する。"""
    path = tmp_path / "cpus"
    with patch.object(Path, "read_text", side_effect=error):
        with pytest.raises(type(error)):
            linux._read_hybrid_cpu_list(path)


@pytest.mark.parametrize("p_cpus", ["2-1", "0,0"])
def test_detect_rejects_invalid_hybrid_sysfs_cpu_list(
    tmp_path: Path,
    p_cpus: str,
) -> None:
    """LinuxのP/E sysfsにある不正なCPUリストを拒否する。"""
    _write_topology(tmp_path, p_cpus, "2", "0-2")
    path_patches = _patch_topology_paths(tmp_path)
    with patch.object(linux, "_is_x86", return_value=True):
        with path_patches:
            with pytest.raises(ValueError, match="CPUリスト|範囲|重複"):
                linux.detect_linux_hybrid_cpu_topology()


def test_detect_rejects_unknown_available_cpu(tmp_path: Path) -> None:
    """Linuxの利用可能集合に分類不能CPUがある場合は拒否する。"""
    _write_topology(tmp_path, "0", "2", "0-2")
    path_patches = _patch_topology_paths(tmp_path)
    threads = _FakeThreads((100,), {100: {0, 1, 2}})
    with patch.object(linux, "_is_x86", return_value=True):
        with path_patches:
            with patch.object(linux, "_list_thread_ids", side_effect=threads.list_ids):
                with patch.object(
                    linux, "_get_thread_affinity", side_effect=threads.get
                ):
                    with pytest.raises(ValueError, match="分類"):
                        linux.detect_linux_hybrid_cpu_topology()


def test_detect_returns_none_when_one_class_is_not_allowed(tmp_path: Path) -> None:
    """Linuxの交差集合でPまたはEの一方が空ならlegacy扱いにする。"""
    _write_topology(tmp_path, "0-1", "2-3", "0-3")
    path_patches = _patch_topology_paths(tmp_path)
    threads = _FakeThreads((100,), {100: {0, 1}})
    with patch.object(linux, "_is_x86", return_value=True):
        with path_patches:
            with patch.object(linux, "_list_thread_ids", side_effect=threads.list_ids):
                with patch.object(
                    linux, "_get_thread_affinity", side_effect=threads.get
                ):
                    assert linux.detect_linux_hybrid_cpu_topology() is None


def test_detect_keeps_only_cpus_in_all_thread_affinities(tmp_path: Path) -> None:
    """Linuxの検出が全TID affinityの共通CPU集合を使う。"""
    _write_topology(tmp_path, "0-1", "2-3", "0-3")
    path_patches = _patch_topology_paths(tmp_path)
    threads = _FakeThreads((100,), {100: {0, 2}})
    with patch.object(linux, "_is_x86", return_value=True):
        with path_patches:
            with patch.object(linux, "_list_thread_ids", side_effect=threads.list_ids):
                with patch.object(
                    linux, "_get_thread_affinity", side_effect=threads.get
                ):
                    topology = linux.detect_linux_hybrid_cpu_topology()

    assert topology is not None
    assert topology.p_logical_cpu_ids == (0,)
    assert topology.e_logical_cpu_ids == (2,)


def test_apply_linux_plan_updates_all_threads() -> None:
    """Linuxの適用が全TIDを計画集合へ制限する。"""
    threads = _FakeThreads((100, 101), {100: {0, 1, 2}, 101: {0, 1, 2}})
    plan = LinuxCpuExecutionPlan(1, (0, 1))
    with patch.object(linux, "_list_thread_ids", side_effect=threads.list_ids):
        with patch.object(linux, "_get_thread_affinity", side_effect=threads.get):
            with patch.object(linux, "_set_thread_affinity", side_effect=threads.set):
                linux.apply_linux_cpu_execution_plan(plan)

    assert threads.masks == {100: frozenset({0, 1}), 101: frozenset({0, 1})}


def test_apply_propagates_detection_unavailable_without_catching() -> None:
    """affinity適用は検出不能専用例外を握りつぶさない。"""
    plan = LinuxCpuExecutionPlan(1, (0, 1))
    with patch.object(linux, "_list_thread_ids", return_value=(100,)):
        with patch.object(
            linux,
            "_get_thread_affinity",
            side_effect=linux._LinuxHybridCpuDetectionUnavailable(),
        ):
            with pytest.raises(linux._LinuxHybridCpuDetectionUnavailable):
                linux.apply_linux_cpu_execution_plan(plan)


def test_apply_linux_plan_targets_all_p_cpus_when_target_exceeds_threads() -> None:
    """Linuxの適用がNより多い全P論理CPUを各TIDへ設定する。"""
    threads = _FakeThreads((100, 101), {100: {0, 1, 2}, 101: {0, 1, 2}})
    plan = LinuxCpuExecutionPlan(2, (0, 1, 2))
    with patch.object(linux, "_list_thread_ids", side_effect=threads.list_ids):
        with patch.object(linux, "_get_thread_affinity", side_effect=threads.get):
            with patch.object(linux, "_set_thread_affinity", side_effect=threads.set):
                linux.apply_linux_cpu_execution_plan(plan)

    assert threads.masks == {100: frozenset({0, 1, 2}), 101: frozenset({0, 1, 2})}


def test_apply_rejects_target_that_is_not_subset_of_any_thread() -> None:
    """Linuxの適用が既存affinityを広げる計画を拒否する。"""
    threads = _FakeThreads((100,), {100: {0, 2}})
    plan = LinuxCpuExecutionPlan(1, (0, 1))
    with patch.object(linux, "_list_thread_ids", side_effect=threads.list_ids):
        with patch.object(linux, "_get_thread_affinity", side_effect=threads.get):
            with patch.object(linux, "_set_thread_affinity", side_effect=threads.set):
                with pytest.raises(ValueError, match="許可していません"):
                    linux.apply_linux_cpu_execution_plan(plan)

    assert threads.set_calls == []


def test_apply_rolls_back_after_partial_failure() -> None:
    """Linuxの適用が途中失敗時に変更済みTIDを戻す。"""
    threads = _FakeThreads((100, 101), {100: {0, 1, 2}, 101: {0, 1, 2}})
    threads.fail_after = 1
    plan = LinuxCpuExecutionPlan(1, (0, 1))
    with patch.object(linux, "_list_thread_ids", side_effect=threads.list_ids):
        with patch.object(linux, "_get_thread_affinity", side_effect=threads.get):
            with patch.object(linux, "_set_thread_affinity", side_effect=threads.set):
                with pytest.raises(OSError, match="affinity設定に失敗"):
                    linux.apply_linux_cpu_execution_plan(plan)

    assert threads.masks == {
        100: frozenset({0, 1, 2}),
        101: frozenset({0, 1, 2}),
    }


def test_apply_reports_rollback_failure() -> None:
    """Linuxのロールバック失敗を状態不定のRuntimeErrorへ変換する。"""
    threads = _FakeThreads((100, 101), {100: {0, 1, 2}, 101: {0, 1, 2}})
    threads.fail_after = 1
    original_set = threads.set

    def fail_rollback(thread_id: int, affinity: frozenset[int]) -> None:
        if len(threads.set_calls) >= 1:
            raise OSError(errno.EPERM, "ロールバックに失敗しました")
        original_set(thread_id, affinity)

    plan = LinuxCpuExecutionPlan(1, (0, 1))
    with patch.object(linux, "_list_thread_ids", side_effect=threads.list_ids):
        with patch.object(linux, "_get_thread_affinity", side_effect=threads.get):
            with patch.object(linux, "_set_thread_affinity", side_effect=fail_rollback):
                with pytest.raises(RuntimeError, match="ロールバック"):
                    linux.apply_linux_cpu_execution_plan(plan)


def test_validate_linux_plan_requires_exact_affinity() -> None:
    """Linuxの検証が全TIDと計画集合の完全一致を要求する。"""
    threads = _FakeThreads((100, 101), {100: {0, 1}, 101: {0, 2}})
    plan = LinuxCpuExecutionPlan(1, (0, 1))
    with patch.object(linux, "_list_thread_ids", side_effect=threads.list_ids):
        with patch.object(linux, "_get_thread_affinity", side_effect=threads.get):
            with pytest.raises(RuntimeError, match="一致しません"):
                linux.validate_linux_cpu_execution_plan(plan)


@pytest.mark.parametrize(
    "plan",
    [
        LinuxCpuExecutionPlan(0, (0,)),
        LinuxCpuExecutionPlan(2, ()),
        LinuxCpuExecutionPlan(2, (0, 1)),
        LinuxCpuExecutionPlan(2, (0, 0)),
    ],
)
def test_apply_rejects_plan_invariant_before_thread_access(
    plan: LinuxCpuExecutionPlan,
) -> None:
    """Linuxの対象論理CPU数がN以下の計画を拒否する。"""
    with patch.object(
        linux,
        "_list_thread_ids",
        side_effect=AssertionError("TIDアクセスは開始されません"),
    ):
        with pytest.raises(ValueError, match="CPU|論理CPU"):
            linux.apply_linux_cpu_execution_plan(plan)


def test_validate_rejects_plan_invariant_before_thread_access() -> None:
    """Linuxの検証が不変条件をTIDアクセス前に確認する。"""
    plan = LinuxCpuExecutionPlan(2, (0, 0))

    with patch.object(
        linux,
        "_list_thread_ids",
        side_effect=AssertionError("TIDアクセスは開始されません"),
    ):
        with pytest.raises(ValueError, match="論理CPU"):
            linux.validate_linux_cpu_execution_plan(plan)
