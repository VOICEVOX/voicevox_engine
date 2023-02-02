from typing import Union

from packaging.version import Version
from packaging.version import parse as parse_version


def parse_core_version(version: str) -> Version:
    return parse_version(version)
