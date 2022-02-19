import sys
from pathlib import Path


def engine_root() -> Path:
    # nuitkaビルドをした際はグローバルに__compiled__が含まれる
    if "__compiled__" in globals():
        root_dir = Path(sys.argv[0]).parent

    # pyinstallerでビルドをした際はsys.frozenが設定される
    elif getattr(sys, "frozen", False):
        root_dir = Path(sys.argv[0]).parent

    else:
        root_dir = Path(__file__).parents[2]

    return root_dir.resolve(strict=True)
