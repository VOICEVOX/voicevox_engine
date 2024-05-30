import json
import os
from argparse import ArgumentParser
from collections.abc import Generator
from hashlib import sha256
from pathlib import Path, PurePosixPath

SPEAKER_INFO_DIR = (Path(__file__).parents[1] / "speaker_info").resolve()
DEFAULT_FILENAME = "filemap.json"


def to_posix_str_path(path: Path) -> str:
    return str(PurePosixPath(path))


def make_hash(file: Path) -> str:
    digest = sha256(file.read_bytes()).digest()
    return digest.hex()


def walk_character_files(
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


def mapping(target: Path) -> dict[str, str]:
    return {
        to_posix_str_path(filepath): filehash
        for filepath, filehash in walk_character_files(target, ("wav", "png"))
    }


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("--save", type=Path)
    parser.add_argument("--target", default=SPEAKER_INFO_DIR, type=Path)
    arg = parser.parse_args()
    target_dir: Path = arg.target
    save: Path = target_dir.parent if arg.save is None else arg.save
    save_file: Path = save if not save.is_dir() else save / DEFAULT_FILENAME
    if not target_dir.is_dir():
        raise Exception()
    mapped = mapping(target_dir)
    with save_file.open(mode="wt", encoding="utf-8") as f:
        json.dump(mapped, f, ensure_ascii=False)


if __name__ == "__main__":
    main()
