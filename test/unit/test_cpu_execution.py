"""`cpu_execution.py` のテスト"""

import os
from unittest.mock import patch

import pytest

from voicevox_engine.cpu_execution import _resolve_cpu_num_threads


@pytest.mark.parametrize(
    ("cpu_num_threads", "logical_cpu_count", "true_num_threads"),
    [(None, 1, 1), (None, 2, 1), (0, 3, 2)],
)
def test_resolve_cpu_num_threads(
    cpu_num_threads: int | None, logical_cpu_count: int, true_num_threads: int
) -> None:
    """`cpu_num_threads`が未指定または0の場合、論理コア数の半分を切り上げた値を返す。"""
    # Outputs
    with patch.object(os, "cpu_count", return_value=logical_cpu_count):
        num_threads = _resolve_cpu_num_threads(cpu_num_threads)
    # Test
    assert true_num_threads == num_threads
