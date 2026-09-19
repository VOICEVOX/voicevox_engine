"""`cpu_execution_linux.py` のテスト"""

import errno
from pathlib import Path
from unittest.mock import patch

import pytest

from voicevox_engine.core import cpu_execution_linux as linux


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("3", {3}),
        ("3-5", {3, 4, 5}),
        ("3,7-8,12", {3, 7, 8, 12}),
    ],
)
def test_parse_cpu_list(value: str, expected: set[int]) -> None:
    """LinuxのCPUリストの単体、範囲、カンマ表記を解釈する。"""
    assert linux._parse_cpu_list(value) == expected


@pytest.mark.parametrize("value", ["", "3-2", "3,,4", "3-", "-3", "3-4-5"])
def test_parse_cpu_list_rejects_invalid(value: str) -> None:
    """Linuxの不正なCPUリストを拒否する。"""
    with pytest.raises(ValueError, match="CPUリスト|範囲|形式|空"):
        linux._parse_cpu_list(value)


def test_parse_cpu_list_rejects_duplicate() -> None:
    """LinuxのCPUリストの重複を拒否する。"""
    with pytest.raises(ValueError, match="重複"):
        linux._parse_cpu_list("1-3,3")


def _patch_paths(tmp_path: Path) -> tuple[Path, Path]:
    p_path = tmp_path / "cpu_core" / "cpus"
    e_path = tmp_path / "cpu_atom" / "cpus"
    p_path.parent.mkdir()
    e_path.parent.mkdir()
    return p_path, e_path


def test_configure_linux_cpu_execution_returns_without_hybrid_sysfs(
    tmp_path: Path,
) -> None:
    """P/E sysfsがなければ警告せずCPU affinityを変更しない。"""
    p_path, e_path = _patch_paths(tmp_path)
    with patch.object(linux, "_CPU_CORE_CPUS_PATH", p_path):
        with patch.object(linux, "_CPU_ATOM_CPUS_PATH", e_path):
            with patch.object(linux, "_is_x86", return_value=True):
                with patch.object(
                    linux,
                    "_list_thread_ids",
                    side_effect=AssertionError("TIDを取得しません"),
                ):
                    linux.configure_linux_cpu_execution(1)


def test_configure_linux_cpu_execution_returns_for_empty_hybrid_sysfs(
    tmp_path: Path,
) -> None:
    """空のP/E sysfsはP/E未検出としてCPU affinityを変更しない。"""
    p_path, e_path = _patch_paths(tmp_path)
    p_path.write_text("", encoding="ascii")
    e_path.write_text("0", encoding="ascii")
    with patch.object(linux, "_CPU_CORE_CPUS_PATH", p_path):
        with patch.object(linux, "_CPU_ATOM_CPUS_PATH", e_path):
            with patch.object(linux, "_is_x86", return_value=True):
                with patch.object(
                    linux,
                    "_list_thread_ids",
                    side_effect=AssertionError("TIDを取得しません"),
                ):
                    linux.configure_linux_cpu_execution(1)


def test_configure_linux_cpu_execution_intersects_thread_affinities_and_sets_once(
    tmp_path: Path,
) -> None:
    """全TIDの初期affinity共通部分からP>Nの集合を一度ずつ設定する。"""
    p_path, e_path = _patch_paths(tmp_path)
    p_path.write_text("0-5", encoding="ascii")
    e_path.write_text("6-7", encoding="ascii")
    thread_ids = (100, 101, 102)
    initial_affinities = {
        100: frozenset({0, 1, 2, 3, 4, 6}),
        101: frozenset({1, 2, 3, 4, 5, 6}),
        102: frozenset({1, 2, 3, 4, 6}),
    }
    set_calls: list[tuple[int, frozenset[int]]] = []

    def set_affinity(thread_id: int, affinity: frozenset[int]) -> None:
        set_calls.append((thread_id, affinity))

    with patch.object(linux, "_CPU_CORE_CPUS_PATH", p_path):
        with patch.object(linux, "_CPU_ATOM_CPUS_PATH", e_path):
            with patch.object(linux, "_is_x86", return_value=True):
                with patch.object(linux, "_list_thread_ids", return_value=thread_ids):
                    with patch.object(
                        linux,
                        "_get_thread_affinity",
                        side_effect=initial_affinities.__getitem__,
                    ):
                        with patch.object(
                            linux, "_set_thread_affinity", side_effect=set_affinity
                        ):
                            linux.configure_linux_cpu_execution(2)

    assert set_calls == [
        (100, frozenset({1, 2, 3, 4})),
        (101, frozenset({1, 2, 3, 4})),
        (102, frozenset({1, 2, 3, 4})),
    ]


def test_configure_linux_cpu_execution_does_not_set_when_common_affinity_has_no_e(
    tmp_path: Path,
) -> None:
    """共通affinityにEコアがなければP>NでもCPU affinityを変更しない。"""
    p_path, e_path = _patch_paths(tmp_path)
    p_path.write_text("0-1", encoding="ascii")
    e_path.write_text("2-3", encoding="ascii")
    thread_ids = (100, 101)
    initial_affinities = {
        100: frozenset({0, 1}),
        101: frozenset({0, 1}),
    }
    with patch.object(linux, "_CPU_CORE_CPUS_PATH", p_path):
        with patch.object(linux, "_CPU_ATOM_CPUS_PATH", e_path):
            with patch.object(linux, "_is_x86", return_value=True):
                with patch.object(linux, "_list_thread_ids", return_value=thread_ids):
                    with patch.object(
                        linux,
                        "_get_thread_affinity",
                        side_effect=initial_affinities.__getitem__,
                    ):
                        with patch.object(
                            linux, "_set_thread_affinity"
                        ) as set_affinity:
                            linux.configure_linux_cpu_execution(1)

    set_affinity.assert_not_called()


@pytest.mark.parametrize("cpu_num_threads", [4, 5])
def test_configure_linux_cpu_execution_does_not_set_when_p_is_not_larger(
    tmp_path: Path,
    cpu_num_threads: int,
) -> None:
    """P数がN以下ならCPU affinityを変更しない。"""
    p_path, e_path = _patch_paths(tmp_path)
    p_path.write_text("0-3", encoding="ascii")
    e_path.write_text("4-5", encoding="ascii")
    with patch.object(linux, "_CPU_CORE_CPUS_PATH", p_path):
        with patch.object(linux, "_CPU_ATOM_CPUS_PATH", e_path):
            with patch.object(linux, "_is_x86", return_value=True):
                with patch.object(linux, "_list_thread_ids", return_value=(100,)):
                    with patch.object(
                        linux,
                        "_get_thread_affinity",
                        return_value=frozenset({0, 1, 2, 3, 4, 5}),
                    ):
                        with patch.object(
                            linux, "_set_thread_affinity"
                        ) as set_affinity:
                            linux.configure_linux_cpu_execution(cpu_num_threads)
    set_affinity.assert_not_called()


def test_configure_linux_cpu_execution_propagates_affinity_error(
    tmp_path: Path,
) -> None:
    """P/E検出後のOS APIエラーを伝播する。"""
    p_path, e_path = _patch_paths(tmp_path)
    p_path.write_text("0-3", encoding="ascii")
    e_path.write_text("4-5", encoding="ascii")
    error = OSError(errno.EPERM, "affinity error")
    with patch.object(linux, "_CPU_CORE_CPUS_PATH", p_path):
        with patch.object(linux, "_CPU_ATOM_CPUS_PATH", e_path):
            with patch.object(linux, "_is_x86", return_value=True):
                with patch.object(linux, "_list_thread_ids", return_value=(100,)):
                    with patch.object(linux, "_get_thread_affinity", side_effect=error):
                        with pytest.raises(OSError, match="affinity error"):
                            linux.configure_linux_cpu_execution(1)


def test_configure_linux_cpu_execution_returns_on_non_x86() -> None:
    """非x86環境ではP/E sysfsを読まない。"""
    with patch.object(linux, "_is_x86", return_value=False):
        with patch.object(
            linux,
            "_read_hybrid_cpu_list",
            side_effect=AssertionError("sysfsを読みません"),
        ):
            linux.configure_linux_cpu_execution(1)
