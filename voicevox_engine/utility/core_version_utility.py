from typing import Sequence

from semver.version import Version


def parse_core_version(version: str) -> Version:
    return Version.parse(version)


def get_latest_core_version(versions: Sequence[str]) -> str:
    if len(versions) == 0:
        raise Exception("versions must be non-empty.")

    return str(max(map(parse_core_version, versions)))
