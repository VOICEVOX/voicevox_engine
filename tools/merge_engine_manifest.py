"""
エンジンマニフェストをマージする。
"""

import argparse
import json
from pathlib import Path

JsonValue = str | int | float


def merge_json_string(src: str, dst: str) -> str:
    src_json: dict[str, JsonValue | dict[str, dict]] = json.loads(src)
    dst_json: dict[str, JsonValue | dict[str, dict]] = json.loads(dst)

    for key, dst_value in dst_json.items():
        assert key in src_json, f"Key {key} is not found in src_json"

        # `manage_library` のみdictなので特別に処理
        if key == "supported_features":
            assert isinstance(dst_value, dict)

            src_value = src_json[key]
            assert isinstance(src_value, dict)
            src_value.update(dst_value)

        else:
            src_value = src_json[key]
            assert isinstance(src_value, JsonValue)
            assert isinstance(dst_value, JsonValue)
            src_json[key] = dst_value

    return json.dumps(src_json, ensure_ascii=False)


def merge_engine_manifest(src_path: Path, dst_path: Path, output_path: Path) -> None:
    src = src_path.read_text(encoding="utf-8")
    dst = dst_path.read_text(encoding="utf-8")
    merged = merge_json_string(src, dst)
    output_path.write_text(merged, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("src_path", type=Path)
    parser.add_argument("dst_path", type=Path)
    parser.add_argument("output_path", type=Path)
    args = parser.parse_args()
    merge_engine_manifest(args.src_path, args.dst_path, args.output_path)
