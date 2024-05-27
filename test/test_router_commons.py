""" ルーター共通処理のテスト"""

from voicevox_engine.app.routers.commons import convert_version_format
from voicevox_engine.core.core_adapter import CoreAdapter
from voicevox_engine.core.core_initializer import CoreManager
from voicevox_engine.dev.core.mock import MockCoreWrapper


def test_convert_version_format_non_latest() -> None:
    """convert_version_format() で明示的バージョンが維持される。"""
    # Inputs
    core_manager = CoreManager()
    api_format_version = "0.0.2"
    # Expects
    true_version = "0.0.2"
    # Outputs
    version = convert_version_format(api_format_version, core_manager)

    # Test
    assert true_version == version


def test_cores_convert_version_format_latest() -> None:
    """convert_version_format() で latest 表現が変換される。"""
    # Inputs
    core_manager = CoreManager()
    core_manager.register_core(CoreAdapter(MockCoreWrapper()), "0.0.1")
    core_manager.register_core(CoreAdapter(MockCoreWrapper()), "0.0.2")
    api_format_version = None
    # Expects
    true_version = "0.0.2"
    # Outputs
    version = convert_version_format(api_format_version, core_manager)

    # Test
    assert true_version == version
