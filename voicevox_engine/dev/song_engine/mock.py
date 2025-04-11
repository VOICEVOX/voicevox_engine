"""SongEngine のモック"""

from ...tts_pipeline.song_engine import (
    SongEngine,
)
from ..core.mock import MockCoreWrapper


class MockSongEngine(SongEngine):
    """製品版コア無しに歌声音声合成可能なモック版SongEngine"""

    def __init__(self) -> None:
        super().__init__(MockCoreWrapper())
