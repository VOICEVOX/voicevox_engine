"""
更新履歴をマージする。
"""

import argparse
import json
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Union


def merge_json_string(src: str, dst: str) -> str:
    """
    バージョンが同じ場合は要素を結合する
    >>> src = '[{"version": "0.0.1", "a": ["a1"], "b": ["b1", "b2"]}]'
    >>> dst = '[{"version": "0.0.1", "a": ["a2"], "b": ["b1", "b3"]}]'
    >>> merge_json_string(src, dst)
    '[{"version": "0.0.1", "a": ["a1", "a2"], "b": ["b1", "b2", "b3"]}]'

    バージョンが無かった場合は無視される
    >>> src = '[{"version": "1"}]'
    >>> dst = '[{"version": "1"}, {"version": "2"}]'
    >>> merge_json_string(src, dst)
    '[{"version": "1"}]'
    """
    src_json: List[Dict[str, Union[str, List[str]]]] = json.loads(src)
    dst_json: List[Dict[str, Union[str, List[str]]]] = json.loads(dst)

    for src_item in src_json:
        for dst_item in dst_json:
            if src_item["version"] == dst_item["version"]:
                for key in src_item:
                    if key == "version":
                        continue

                    # 異なるものがあった場合だけ後ろに付け足す
                    src_item[key] = list(
                        OrderedDict.fromkeys(src_item[key] + dst_item[key])
                    )

    return json.dumps(src_json)


def merge_update_infos(src_path: Path, dst_path: Path, output_path: Path) -> None:
    src = src_path.read_text(encoding="utf-8")
    dst = dst_path.read_text(encoding="utf-8")
    merged = merge_json_string(src, dst)
    output_path.write_text(merged)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("src_path", type=Path)
    parser.add_argument("dst_path", type=Path)
    parser.add_argument("output_path", type=Path)
    args = parser.parse_args()
    merge_update_infos(args.src_path, args.dst_path, args.output_path)
