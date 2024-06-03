"""エンジンマニフェストのテスト"""

from pathlib import Path

from voicevox_engine.engine_manifest import ManifestWrapper


def test_ManifestWrapper_init() -> None:
    """`ManifestWrapper.from_file()` でインスタンスが生成される。"""
    ManifestWrapper.from_file(Path("engine_manifest.json"))
    assert True


def test_ManifestWrapper_relative_path() -> None:
    """`ManifestWrapper.root` を用いて相対パスが解決できる。"""
    wrapper = ManifestWrapper.from_file(Path("engine_manifest.json"))
    tos_path = wrapper.root / wrapper.terms_of_service
    assert tos_path.exists()
