"""`cpu_execution_linux.py` のテスト"""

import os
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


def _prepare_cpu_list_paths(tmp_path: Path) -> tuple[Path, Path]:
    p_path = tmp_path / "cpu_core" / "cpus"
    e_path = tmp_path / "cpu_atom" / "cpus"
    p_path.parent.mkdir()
    e_path.parent.mkdir()
    return p_path, e_path


def test_configure_linux_cpu_execution_returns_without_hybrid_sysfs(
    tmp_path: Path,
) -> None:
    """P/E sysfsがなければCPU affinityを変更しない。"""
    p_path, e_path = _prepare_cpu_list_paths(tmp_path)
    with patch.object(linux, "_CPU_CORE_CPUS_PATH", p_path):
        with patch.object(linux, "_CPU_ATOM_CPUS_PATH", e_path):
            linux.configure_linux_cpu_execution(1)


def test_configure_linux_cpu_execution_sets_all_available_p_cpus_once(
    tmp_path: Path,
) -> None:
    """利用可能なPコアがNより多ければ呼び出し元TIDへ一度設定する。"""
    p_path, e_path = _prepare_cpu_list_paths(tmp_path)
    p_path.write_text("0-5", encoding="ascii")
    e_path.write_text("6-7", encoding="ascii")
    with patch.object(linux, "_CPU_CORE_CPUS_PATH", p_path):
        with patch.object(linux, "_CPU_ATOM_CPUS_PATH", e_path):
            with patch.object(
                os,
                "sched_getaffinity",
                return_value={0, 1, 2, 3, 6},
                create=True,
            ):
                with patch.object(os, "sched_setaffinity", create=True) as set_affinity:
                    linux.configure_linux_cpu_execution(2)

    set_affinity.assert_called_once_with(0, {0, 1, 2, 3})


def test_configure_linux_cpu_execution_does_not_set_without_available_e_cpus(
    tmp_path: Path,
) -> None:
    """利用可能なEコアがなければCPU affinityを変更しない。"""
    p_path, e_path = _prepare_cpu_list_paths(tmp_path)
    p_path.write_text("0-3", encoding="ascii")
    e_path.write_text("4-5", encoding="ascii")
    with patch.object(linux, "_CPU_CORE_CPUS_PATH", p_path):
        with patch.object(linux, "_CPU_ATOM_CPUS_PATH", e_path):
            with patch.object(
                os,
                "sched_getaffinity",
                return_value={0, 1, 2, 3},
                create=True,
            ):
                with patch.object(os, "sched_setaffinity", create=True) as set_affinity:
                    linux.configure_linux_cpu_execution(1)

    set_affinity.assert_not_called()


@pytest.mark.parametrize("cpu_num_threads", [4, 5])
def test_configure_linux_cpu_execution_does_not_set_when_p_is_not_larger(
    tmp_path: Path,
    cpu_num_threads: int,
) -> None:
    """利用可能なPコア数がN以下ならCPU affinityを変更しない。"""
    p_path, e_path = _prepare_cpu_list_paths(tmp_path)
    p_path.write_text("0-3", encoding="ascii")
    e_path.write_text("4-5", encoding="ascii")
    with patch.object(linux, "_CPU_CORE_CPUS_PATH", p_path):
        with patch.object(linux, "_CPU_ATOM_CPUS_PATH", e_path):
            with patch.object(
                os,
                "sched_getaffinity",
                return_value={0, 1, 2, 3, 4, 5},
                create=True,
            ):
                with patch.object(os, "sched_setaffinity", create=True) as set_affinity:
                    linux.configure_linux_cpu_execution(cpu_num_threads)

    set_affinity.assert_not_called()
