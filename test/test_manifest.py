"""マニフェストのテスト"""

from pathlib import Path

from voicevox_engine.engine_manifest import ManifestContainer


def test_ManifestContainer_init() -> None:
    """`ManifestContainer.from_file()` でインスタンスが生成される。"""
    ManifestContainer.from_file(Path("engine_manifest.json"))
    assert True


def test_ManifestContainer_relative_path() -> None:
    """`ManifestContainer.root` を用いてマニフェスト内の相対パスが解決できる。"""
    container = ManifestContainer.from_file(Path("engine_manifest.json"))
    tos_path = container.root / container.terms_of_service
    assert tos_path.exists()
