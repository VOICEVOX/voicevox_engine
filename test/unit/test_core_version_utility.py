"""
コアバージョンに関する utilities のテスト
"""

from voicevox_engine.utility.core_version_utility import get_latest_version


def test_get_latest_version_same_preview_normal() -> None:
    """`get_latest_version()` は同一バージョンの preview 版より正規版を優先する。"""

    # Inputs
    versions = [
        "0.0.0",
        "0.1.0",
        "0.10.0",
        "0.10.0-preview.1",
        "0.14.0",
        "0.14.0-preview.1",
        "0.14.0-preview.10",
    ]

    # Expects
    true_latest = "0.14.0"

    # Outputs
    latest = get_latest_version(versions)

    # Tests
    assert true_latest == latest


def test_get_latest_version_newer_preview() -> None:
    """`get_latest_version()` は旧バージョンの正規版より新バージョンの preview 版を優先する。"""

    # Inputs
    versions = [
        "0.14.0",
        "0.15.0-preview.1",
    ]

    # Expects
    true_latest = "0.15.0-preview.1"

    # Outputs
    latest = get_latest_version(versions)

    # Tests
    assert true_latest == latest
