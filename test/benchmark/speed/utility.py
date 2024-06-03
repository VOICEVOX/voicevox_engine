"""速度ベンチマーク用のユーティリティ"""

import time
from typing import Callable


def benchmark_time(
    target_function: Callable[[], None], n_repeat: int, sec_sleep: float = 1.0
) -> float:
    """対象関数の平均実行時間を計測する。"""
    scores: list[float] = []
    for _ in range(n_repeat):
        start = time.perf_counter()
        target_function()
        end = time.perf_counter()
        scores += [end - start]
        time.sleep(sec_sleep)
    average = sum(scores) / len(scores)
    return average
