from semver.version import Version


def get_latest_core_version(versions: list[str]) -> str:
    if len(versions) == 0:
        raise Exception("versions must be non-empty.")
    return str(max(map(Version.parse, versions)))
