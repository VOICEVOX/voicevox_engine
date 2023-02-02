from typing import Iterable

from packaging.version import Version
from packaging.version import parse as parse_version


def parse_core_version(version: str) -> Version:
    return parse_version(version)


def get_latest_core_version(versions: Iterable[str]) -> str:
    if len(versions) == 0:
        raise Exception('versions must be non-empty.')

    return str(
        max(map(parse_core_version, versions))
    )
