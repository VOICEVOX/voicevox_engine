"""TTSEngine のモック"""

import copy
from typing import Final

import numpy as np
from numpy.typing import NDArray
from pyopenjtalk import tts

from ...metas.Metas import StyleId
from ...model import AudioQuery
from ...tts_pipeline.tts_engine import (
    TTSEngine,
    raw_wave_to_output_wave,
    to_flatten_moras,
)
from ..core.mock import MockCoreWrapper


class MockTTSEngine(TTSEngine):
    """製品版コア無しに音声合成が可能なモック版TTSEngine"""

    def __init__(self) -> None:
        super().__init__(MockCoreWrapper())

    def synthesize_wave(
        self,
        query: AudioQuery,
        style_id: StyleId,
        enable_interrogative_upspeak: bool = True,
    ) -> NDArray[np.float32]:
        """音声合成用のクエリに含まれる読み仮名に基づいてOpenJTalkで音声波形を生成する。モーラごとの調整は反映されない。"""
        # モーフィング時などに同一参照のqueryで複数回呼ばれる可能性があるので、元の引数のqueryに破壊的変更を行わない
        query = copy.deepcopy(query)

        # recall text in katakana
        flatten_moras = to_flatten_moras(query.accent_phrases)
        kana_text = "".join([mora.text for mora in flatten_moras])

        raw_wave, sr_raw_wave = self.forward(kana_text)
        wave = raw_wave_to_output_wave(query, raw_wave, sr_raw_wave)
        return wave

    def forward(self, text: str) -> tuple[NDArray[np.float32], int]:
        """文字列から pyopenjtalk を用いて音声を合成する。"""
        OJT_SAMPLING_RATE: Final = 48000
        OJT_AMPLITUDE_MAX: Final = 2 ** (16 - 1)
        raw_wave: NDArray[np.float64] = tts(text)[0]
        raw_wave /= OJT_AMPLITUDE_MAX
        return raw_wave.astype(np.float32), OJT_SAMPLING_RATE
