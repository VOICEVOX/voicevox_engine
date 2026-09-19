"""`cpu_execution.py` のテスト"""

from typing import cast
from unittest.mock import patch

import pytest

from voicevox_engine.core import cpu_execution


@pytest.mark.parametrize("cpu_num_threads", [1, 65535])
def test_configure_cpu_execution_uses_explicit_value(cpu_num_threads: int) -> None:
    """明示したCPUスレッド数をそのまま返す。"""
    with patch(
        "voicevox_engine.core.cpu_execution.platform.system", return_value="Other"
    ):
        with patch(
            "voicevox_engine.core.cpu_execution.psutil.cpu_count",
            side_effect=AssertionError("CPU数を取得しません"),
        ):
            assert (
                cpu_execution.configure_cpu_execution(cpu_num_threads)
                == cpu_num_threads
            )


@pytest.mark.parametrize("cpu_num_threads", [None, 0])
def test_configure_cpu_execution_resolves_automatic_value(
    cpu_num_threads: int | None,
) -> None:
    """未指定または0を論理CPU数の半分へ解決する。"""
    with patch(
        "voicevox_engine.core.cpu_execution.platform.system", return_value="Other"
    ):
        with patch(
            "voicevox_engine.core.cpu_execution.psutil.cpu_count", return_value=9
        ) as cpu_count:
            assert cpu_execution.configure_cpu_execution(cpu_num_threads) == 4
    cpu_count.assert_called_once_with(logical=True)


def test_configure_cpu_execution_returns_zero_when_cpu_count_is_unknown() -> None:
    """論理CPU数を取得できなければ0を返す。"""
    with patch(
        "voicevox_engine.core.cpu_execution.psutil.cpu_count", return_value=None
    ):
        with patch(
            "voicevox_engine.core.cpu_execution.platform.system",
            side_effect=AssertionError("OS判定をしません"),
        ):
            assert cpu_execution.configure_cpu_execution(None) == 0


@pytest.mark.parametrize("cpu_num_threads", [True, False, -1, 65536, "4"])
def test_configure_cpu_execution_rejects_invalid_value_before_os_access(
    cpu_num_threads: object,
) -> None:
    """不正なCPUスレッド数をOS情報の取得前に拒否する。"""
    with patch(
        "voicevox_engine.core.cpu_execution.platform.system",
        side_effect=AssertionError("OS判定をしません"),
    ):
        with patch(
            "voicevox_engine.core.cpu_execution.psutil.cpu_count",
            side_effect=AssertionError("CPU数を取得しません"),
        ):
            with pytest.raises(ValueError, match="cpu_num_threads"):
                cpu_execution.configure_cpu_execution(cast(int | None, cpu_num_threads))


@pytest.mark.parametrize(
    ("system", "module_path", "function_name"),
    [
        (
            "Windows",
            "voicevox_engine.core.cpu_execution_windows",
            "configure_windows_cpu_execution",
        ),
        (
            "Linux",
            "voicevox_engine.core.cpu_execution_linux",
            "configure_linux_cpu_execution",
        ),
    ],
)
def test_configure_cpu_execution_dispatches_supported_os(
    system: str,
    module_path: str,
    function_name: str,
) -> None:
    """WindowsとLinuxの設定関数へ解決済みNを渡す。"""
    with patch(
        "voicevox_engine.core.cpu_execution.platform.system", return_value=system
    ):
        with patch(
            "voicevox_engine.core.cpu_execution.psutil.cpu_count", return_value=8
        ):
            with patch(f"{module_path}.{function_name}") as configure:
                assert cpu_execution.configure_cpu_execution(None) == 4
    configure.assert_called_once_with(4)


@pytest.mark.parametrize("system", ["Darwin", "FreeBSD", "Other"])
def test_configure_cpu_execution_does_not_change_unsupported_os(system: str) -> None:
    """macOSなどの未対応環境ではCPU affinityを変更しない。"""
    with patch(
        "voicevox_engine.core.cpu_execution.platform.system", return_value=system
    ):
        assert cpu_execution.configure_cpu_execution(3) == 3
