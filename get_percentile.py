import argparse
import statistics
from pathlib import Path
from typing import List

import numpy as np


def get_percentile(
    naist_jdic_path: Path,
    pos: str,
    pos_detail_1: str,
    pos_detail_2: str,
    pos_detail_3: str,
) -> List[int]:
    costs = []
    with naist_jdic_path.open(encoding="utf-8") as f:
        for line in f:
            (
                _,
                _,
                _,
                _cost,
                _pos,
                _pos_detail_1,
                _pos_detail_2,
                _pos_detail_3,
                _,
                _,
                _,
                _,
                _,
                _,
                _,
            ) = line.split(",")
            if (_pos, _pos_detail_1, _pos_detail_2, _pos_detail_3) == (
                pos,
                pos_detail_1,
                pos_detail_2,
                pos_detail_3,
            ):
                costs.append(int(_cost))
    assert len(costs) > 0
    cost_min = min(costs) - 1
    cost_1per = np.quantile(costs, 0.01).astype(np.int64)
    cost_mode = statistics.mode(costs)
    cost_99per = np.quantile(costs, 0.99).astype(np.int64)
    cost_max = max(costs) + 1
    return (
        [cost_min]
        + [int(cost_1per + (cost_mode - cost_1per) * i / 4) for i in range(5)]
        + [int(cost_mode + (cost_99per - cost_mode) * i / 4) for i in range(1, 5)]
        + [cost_max]
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--naist_jdic_path", type=Path)
    parser.add_argument("--pos", type=str)
    parser.add_argument("--pos_detail_1", type=str)
    parser.add_argument("--pos_detail_2", type=str)
    parser.add_argument("--pos_detail_3", type=str)
    args = parser.parse_args()
    print(
        get_percentile(
            naist_jdic_path=args.naist_jdic_path,
            pos=args.pos,
            pos_detail_1=args.pos_detail_1,
            pos_detail_2=args.pos_detail_2,
            pos_detail_3=args.pos_detail_3,
        )
    )
