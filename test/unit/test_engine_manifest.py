"""エンジンマニフェストのテスト"""

from pathlib import Path

from voicevox_engine.engine_manifest import EngineManifestInternal


def test_manifest_internal_init() -> None:
    """`EngineManifestInternal.from_file()` でインスタンスが生成される。"""
    EngineManifestInternal.from_file(Path("engine_manifest.json"))
    assert True


def test_manifest_internal_relative_path() -> None:
    """`EngineManifestInternal.root` を用いて相対パスが解決できる。"""
    wrapper = EngineManifestInternal.from_file(Path("engine_manifest.json"))
    tos_path = wrapper.root / wrapper.terms_of_service
    assert tos_path.exists()
