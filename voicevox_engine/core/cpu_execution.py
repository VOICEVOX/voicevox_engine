"""CPU実行設定の解決と適用"""

import platform
from typing import cast

import psutil


def _resolve_cpu_num_threads(cpu_num_threads: int | None) -> int:
    if cpu_num_threads is not None:
        if cpu_num_threads != 0:
            if not 1 <= cpu_num_threads <= 65535:
                raise ValueError(
                    "cpu_num_threadsは0、または1以上65535以下で指定してください。"
                )
            return cpu_num_threads

    logical_cpu_count = cast(int | None, psutil.cpu_count(logical=True))
    if logical_cpu_count is None:
        return 0
    return logical_cpu_count // 2


def configure_cpu_execution(cpu_num_threads: int | None) -> int:
    """CPUスレッド数を解決し、必要ならPコアへCPU affinityを設定する。"""
    resolved_cpu_num_threads = _resolve_cpu_num_threads(cpu_num_threads)
    if resolved_cpu_num_threads == 0:
        return resolved_cpu_num_threads

    system = platform.system()
    if system == "Windows":
        from voicevox_engine.core.cpu_execution_windows import (
            configure_windows_cpu_execution,
        )

        configure_windows_cpu_execution(resolved_cpu_num_threads)
    elif system == "Linux":
        from voicevox_engine.core.cpu_execution_linux import (
            configure_linux_cpu_execution,
        )

        configure_linux_cpu_execution(resolved_cpu_num_threads)

    return resolved_cpu_num_threads
