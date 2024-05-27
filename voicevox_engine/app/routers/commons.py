"""ルーター間で共通する処理"""

from typing import TypeAlias

from voicevox_engine.core.core_initializer import CoreManager


APICoreVersion: TypeAlias = str | None # `None` は latest を意味する
EngineCoreVersion: TypeAlias = str


def convert_version_format(core_version: APICoreVersion, core_manager: CoreManager) -> EngineCoreVersion:
    """
    バージョンの形式を API 形式から ENGINE 形式へ変換する。

    API 形式は latest を指定でき、それは `None` で表現される。
    ENGINE 形式は latest を指定できず、ゆえに `None` を持たない。
    """
    return core_manager.latest_version() if core_version is None else core_version
