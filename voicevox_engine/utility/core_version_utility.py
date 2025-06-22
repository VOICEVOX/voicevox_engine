"""バージョンに関する utility"""

from typing import Final

from semver.version import Version

MOCK_CORE_VERSION: Final = "0.0.0"


def get_latest_version(versions: list[str]) -> str:
    """一覧の中で最も新しいバージョン番号を出力する。"""
    if len(versions) == 0:
        raise Exception("versions must be non-empty.")
    return str(max(map(Version.parse, versions)))
