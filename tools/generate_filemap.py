"""
'ResourceManager'が参照するfilemapを予め生成する。
"""

import json
import os
from argparse import ArgumentParser
from collections.abc import Generator
from hashlib import sha256
from pathlib import Path, PurePosixPath

FILEMAP_FILENAME = "filemap.json"
DEFAULT_TARGET_SUFFIX = ["png", "wav"]


# WindowsとPOSIXで同じファイルが生成されるようにPurePosixPathに変換してから文字列にする。
def to_posix_str_path(path: Path) -> str:
    return str(PurePosixPath(path))


def make_hash(file: Path) -> str:
    digest = sha256(file.read_bytes()).digest()
    return digest.hex()


def walk_target_dir(target_dir: Path) -> Generator[Path, None, None]:
    for root, _, files in os.walk(target_dir):
        for file in files:
            yield Path(root, file)


def generate_path_to_hash_dict(
    target_dir: Path, target_suffix: list[str]
) -> dict[str, str]:
    suffix = tuple(target_suffix)
    return {
        to_posix_str_path(filepath.relative_to(target_dir)): make_hash(filepath)
        for filepath in walk_target_dir(target_dir)
        if filepath.suffix.endswith(suffix)
    }


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "--target_dir", type=Path, required=True, help="filemapを作成するディレクトリ"
    )
    parser.add_argument(
        "--target_suffix",
        nargs="+",
        default=DEFAULT_TARGET_SUFFIX,
        help=f"filemapに登録するファイルの拡張子\nデフォルトは{', '.join(DEFAULT_TARGET_SUFFIX)}",
    )
    args = parser.parse_args()

    target_dir: Path = args.target_dir
    if not target_dir.is_dir():
        raise Exception(f"{target_dir}はディレクトリではありません")

    save_path = target_dir / FILEMAP_FILENAME
    path_to_hash = generate_path_to_hash_dict(target_dir, args.target_suffix)
    save_path.write_text(json.dumps(path_to_hash, ensure_ascii=False), encoding="utf-8")
