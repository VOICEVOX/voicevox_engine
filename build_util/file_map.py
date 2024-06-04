"""
'ResourceManager'が参照するファイルを生成
"""

import json
import os
from argparse import ArgumentParser
from collections.abc import Generator
from hashlib import sha256
from pathlib import Path, PurePosixPath

DEFAULT_FILENAME = "filemap.json"
DEFAULT_TARGET_SUFFIX = ["png", "wav"]


def to_posix_str_path(path: Path) -> str:
    return str(PurePosixPath(path))


def make_hash(file: Path) -> str:
    digest = sha256(file.read_bytes()).digest()
    return digest.hex()


def walk_target_dir(
    character_dir: Path, suffix: tuple[str, ...]
) -> Generator[tuple[Path, str], None, None]:
    for root, _, files in os.walk(character_dir):
        for file in files:
            filepath = Path(root, file)
            if not filepath.suffix.endswith(suffix):
                continue
            filehash = make_hash(filepath)
            relative = filepath.relative_to(character_dir)
            yield (relative, filehash)


def generate_path_to_hash_dict(
    target_dir: Path, target_suffix: list[str]
) -> dict[str, str]:
    suffix = tuple(target_suffix)
    return {
        to_posix_str_path(filepath): filehash
        for filepath, filehash in walk_target_dir(target_dir, suffix)
    }


def main() -> None:
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
    arg = parser.parse_args()
    target_dir: Path = arg.target_dir
    if not target_dir.is_dir():
        raise Exception(f"{target_dir}はディレクトリではありません")
    save_path = target_dir.parent / DEFAULT_FILENAME
    path_to_hash = generate_path_to_hash_dict(target_dir, arg.target_suffix)
    save_path.write_text(json.dumps(path_to_hash, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
