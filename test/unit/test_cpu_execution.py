"""`cpu_execution.py` のテスト"""

from unittest.mock import patch

import pytest

from voicevox_engine.core import cpu_execution


@pytest.mark.parametrize("cpu_num_threads", [1, 65535])
def test_configure_cpu_execution_uses_explicit_value(cpu_num_threads: int) -> None:
    """明示したCPUスレッド数をそのまま返す。"""
    with patch(
        "voicevox_engine.core.cpu_execution.platform.system", return_value="Other"
    ):
        assert cpu_execution.configure_cpu_execution(cpu_num_threads) == cpu_num_threads


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
        ):
            assert cpu_execution.configure_cpu_execution(cpu_num_threads) == 4


def test_configure_cpu_execution_returns_zero_when_cpu_count_is_unknown() -> None:
    """論理CPU数を取得できなければ0を返す。"""
    with patch(
        "voicevox_engine.core.cpu_execution.psutil.cpu_count", return_value=None
    ):
        assert cpu_execution.configure_cpu_execution(None) == 0


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


def test_configure_cpu_execution_does_not_change_unsupported_os() -> None:
    """macOSなどの未対応環境ではCPU affinityを変更しない。"""
    with patch(
        "voicevox_engine.core.cpu_execution.platform.system", return_value="Other"
    ):
        with patch(
            "voicevox_engine.core.cpu_execution_windows.configure_windows_cpu_execution"
        ) as configure_windows:
            with patch(
                "voicevox_engine.core.cpu_execution_linux.configure_linux_cpu_execution"
            ) as configure_linux:
                assert cpu_execution.configure_cpu_execution(3) == 3

    configure_windows.assert_not_called()
    configure_linux.assert_not_called()
