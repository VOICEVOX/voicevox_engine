"""
voicevox_engine/part_of_speech_data.pyのcost_candidatesを計算するプログラムです。
引数のnaist_jdic_pathには、open_jtalkのsrc/mecab-naist-jdic/naist-jdic.csvを指定してください。

実行例:
python get_cost_candidates.py --naist_jdic_path=/path/to/naist-jdic.csv \
    --pos=名詞 \
    --pos_detail_1=固有名詞 \
    --pos_detail_2=一般 \
    --pos_detail_3=*

cost_candidatesの値の詳細は以下の通りです。
- 1番目の値はnaist_jdic内の同一品詞の最小コストから1を引いたもの、11番目の値は最大コストに1を足したものです。
- 2番目の値はnaist_jdic内の同一品詞のコストの下位1%、10番目の値は99%の値です。
- 6番目の値はnaist_jdic内の同一品詞のコストの最頻値です。
- 2番目から6番目、6番目から10番目までの値は一定割合で増加するようになっています。
"""

import argparse
import statistics
from pathlib import Path
from typing import List

import numpy as np


def get_candidates(
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
        get_candidates(
            naist_jdic_path=args.naist_jdic_path,
            pos=args.pos,
            pos_detail_1=args.pos_detail_1,
            pos_detail_2=args.pos_detail_2,
            pos_detail_3=args.pos_detail_3,
        )
    )
