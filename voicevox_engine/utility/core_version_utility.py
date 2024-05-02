from semver.version import Version


def get_latest_core_version(versions: list[str]) -> str:
    """一覧の中で最も新しいコアのバージョン番号を出力する。"""
    if len(versions) == 0:
        raise Exception("versions must be non-empty.")
    return str(max(map(Version.parse, versions)))
