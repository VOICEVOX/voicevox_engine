"""TTSEngine のモック"""

import copy
from collections.abc import Iterator
from typing import Final

import numpy as np
from numpy.typing import NDArray
from pyopenjtalk import tts

from ...metas.metas import StyleId
from ...model import AudioQuery
from ...tts_pipeline.audio_postprocessing import raw_wave_to_output_wave
from ...tts_pipeline.kana_converter import create_kana
from ...tts_pipeline.tts_engine import (
    TTSEngine,
    apply_interrogative_upspeak,
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
        enable_interrogative_upspeak: bool,
    ) -> NDArray[np.float32]:
        """音声合成用のクエリに含まれる読み仮名に基づいてOpenJTalkで音声波形を生成する。モーラごとの調整は反映されない。"""
        # 不正なスタイルIDが渡されたときの動作を製品版に揃えるため、スタイルの存在チェックをする
        self._core._assert_style_supports_feature(style_id, "talk")

        # モーフィング時などに同一参照のqueryで複数回呼ばれる可能性があるので、元の引数のqueryに破壊的変更を行わない
        query = copy.deepcopy(query)

        # recall text in katakana
        flatten_moras = to_flatten_moras(query.accent_phrases)
        kana_text = "".join([mora.text for mora in flatten_moras])

        raw_wave, sr_raw_wave = self.forward(kana_text)
        wave = raw_wave_to_output_wave(query, raw_wave, sr_raw_wave)
        return wave

    def synthesize_wave_chunks(
        self,
        query: AudioQuery,
        style_id: StyleId,
        enable_interrogative_upspeak: bool,
        min_accent_phrases: int = 4,
    ) -> Iterator[NDArray[np.float32]]:
        """音声合成用のクエリに含まれる読み仮名を複数アクセント句ごとに音声波形へ変換する。"""
        self._core._assert_style_supports_feature(style_id, "talk")
        query = copy.deepcopy(query)
        query.accent_phrases = apply_interrogative_upspeak(
            query.accent_phrases, enable_interrogative_upspeak
        )

        sampling_rate = 48000
        if len(query.accent_phrases) == 0:
            duration = (query.prePhonemeLength + query.postPhonemeLength) / query.speedScale
            raw_wave = np.zeros(max(1, int(duration * sampling_rate)), dtype=np.float32)
            yield raw_wave_to_output_wave(query, raw_wave, sampling_rate)
            return

        min_accent_phrases = max(1, min_accent_phrases)
        chunk_accent_phrases_list = [
            query.accent_phrases[start : start + min_accent_phrases]
            for start in range(0, len(query.accent_phrases), min_accent_phrases)
        ]
        if (
            len(chunk_accent_phrases_list) >= 2
            and len(chunk_accent_phrases_list[-1]) < min_accent_phrases
        ):
            chunk_accent_phrases_list[-2].extend(chunk_accent_phrases_list[-1])
            chunk_accent_phrases_list.pop()

        for i, accent_phrases in enumerate(chunk_accent_phrases_list):
            kana_text = create_kana(accent_phrases)
            raw_wave, sr_raw_wave = self.forward(kana_text)
            if i == 0:
                pre_silence_length = int(
                    query.prePhonemeLength / query.speedScale * sr_raw_wave
                )
                raw_wave = np.concatenate(
                    [np.zeros(pre_silence_length, dtype=np.float32), raw_wave]
                )
            if i == len(chunk_accent_phrases_list) - 1:
                post_silence_length = int(
                    query.postPhonemeLength / query.speedScale * sr_raw_wave
                )
                raw_wave = np.concatenate(
                    [raw_wave, np.zeros(post_silence_length, dtype=np.float32)]
                )
            yield raw_wave_to_output_wave(query, raw_wave, sr_raw_wave)

    def forward(self, text: str) -> tuple[NDArray[np.float32], int]:
        """文字列から pyopenjtalk を用いて音声を合成する。"""
        OJT_SAMPLING_RATE: Final = 48000
        OJT_AMPLITUDE_MAX: Final = 2 ** (16 - 1)
        raw_wave: NDArray[np.float64] = tts(text)[0]
        raw_wave /= OJT_AMPLITUDE_MAX
        return raw_wave.astype(np.float32), OJT_SAMPLING_RATE
