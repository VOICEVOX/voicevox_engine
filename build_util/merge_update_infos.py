"""
更新履歴を整形する。
"""

import argparse
import json
from pathlib import Path


def reformat_update_info(file_path: Path) -> None:
    update_info = file_path.read_text(encoding="utf-8")
    reformated = json.dumps(json.loads(update_info))
    file_path.write_text(reformated)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("src_path", type=Path)
    args = parser.parse_args()
    reformat_update_info(args.src_path)
