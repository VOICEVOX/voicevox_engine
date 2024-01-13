import copy
from logging import getLogger
from typing import Any

import numpy as np
from numpy.typing import NDArray
from pyopenjtalk import tts
from soxr import resample

from ...metas.Metas import StyleId
from ...model import AudioQuery
from ...tts_pipeline.tts_engine import TTSEngine, to_flatten_moras
from ..core.mock import MockCoreWrapper


class MockTTSEngine(TTSEngine):
    """製品版コア無しに音声合成が可能なモック版TTSEngine"""

    def __init__(self):
        super().__init__(MockCoreWrapper())

    def synthesize_wave(
        self,
        query: AudioQuery,
        style_id: StyleId,
        enable_interrogative_upspeak: bool = True,
    ) -> NDArray[np.float32]:
        """音声合成用のクエリに含まれる読み仮名に基づいてOpenJTalkで音声波形を生成する"""
        # モーフィング時などに同一参照のqueryで複数回呼ばれる可能性があるので、元の引数のqueryに破壊的変更を行わない
        query = copy.deepcopy(query)

        # recall text in katakana
        flatten_moras = to_flatten_moras(query.accent_phrases)
        kana_text = "".join([mora.text for mora in flatten_moras])

        wave = self.forward(kana_text)

        # volume
        wave *= query.volumeScale

        return wave

    def forward(self, text: str, **kwargs: dict[str, Any]) -> NDArray[np.float32]:
        """
        forward tts via pyopenjtalk.tts()
        参照→TTSEngine のdocstring [Mock]

        Parameters
        ----------
        text : str
            入力文字列（例：読み上げたい文章をカタカナにした文字列、等）

        Returns
        -------
        wave [NDArray[np.float32]]
            音声波形データをNumPy配列で返します

        Note
        -------
        ここで行う音声合成では、調声（ピッチ等）を反映しない

        # pyopenjtalk.tts()の出力仕様
        dtype=np.float64, 16 bit, mono 48000 Hz

        # resampleの説明
        非モック実装（decode_forward）と合わせるために、出力を24kHz、32bit浮動小数に変換した。
        """
        logger = getLogger("uvicorn")  # FastAPI / Uvicorn 内からの利用のため
        logger.info("[Mock] input text: %s" % text)
        wave, sr = tts(text)
        wave /= 2**15
        wave = resample(wave, 48000, 24000)
        return wave.astype(np.float32)
