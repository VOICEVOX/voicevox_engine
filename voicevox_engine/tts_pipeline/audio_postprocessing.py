"""音声波形を加工する。"""

from collections.abc import Iterator

import numpy as np
from numpy.typing import NDArray
from soxr import ResampleStream, resample

from ..model import AudioQuery
from .model import (
    FrameAudioQuery,
)


def raw_wave_stream_to_output_wave(
    query: AudioQuery | FrameAudioQuery,
    raw_wave_length: int,
    stream: Iterator[NDArray[np.float32]],
    sr_wave: int,
) -> tuple[int, Iterator[NDArray[np.float32]]]:
    """生音声波形に音声合成用のクエリを適用して出力音声波形を生成する（ストリーミング用）"""
    wave_length = raw_wave_length
    output_rate = query.outputSamplingRate

    if sr_wave != output_rate:
        wave_length = (raw_wave_length * output_rate + sr_wave // 2) // sr_wave

    def volume_scale_stream(
        stream: Iterator[NDArray[np.float32]],
    ) -> Iterator[NDArray[np.float32]]:
        for wave in stream:
            yield _apply_volume_scale(wave, query)

    def resample_stream(
        stream: Iterator[NDArray[np.float32]],
    ) -> Iterator[NDArray[np.float32]]:
        # サンプリングレート一致のときはスルー
        if sr_wave == output_rate:
            yield from stream
            return
        # ResampleStreamには最後の入力を明示する必要があるので予め取り出しておく
        buffer = next(stream)
        resampler = ResampleStream(sr_wave, output_rate, 1, buffer.dtype)

        for raw_wave in stream:
            chunk = resampler.resample_chunk(buffer)
            buffer = raw_wave
            yield chunk

        yield resampler.resample_chunk(buffer, True)

    def output_stereo_stream(
        stream: Iterator[NDArray[np.float32]],
    ) -> Iterator[NDArray[np.float32]]:
        for wave in stream:
            yield _apply_output_stereo(wave, query)

    return wave_length, output_stereo_stream(
        resample_stream(volume_scale_stream(stream))
    )


def raw_wave_to_output_wave(
    query: AudioQuery | FrameAudioQuery, wave: NDArray[np.float32], sr_wave: int
) -> NDArray[np.float32]:
    """生音声波形に音声合成用のクエリを適用して出力音声波形を生成する"""
    wave = _apply_volume_scale(wave, query)
    wave = _apply_output_sampling_rate(wave, sr_wave, query)
    wave = _apply_output_stereo(wave, query)
    return wave


def _apply_volume_scale(
    wave: NDArray[np.float32], query: AudioQuery | FrameAudioQuery
) -> NDArray[np.float32]:
    """音声波形へ音声合成用のクエリがもつ音量スケール（`volumeScale`）を適用する"""
    return wave * query.volumeScale


def _apply_output_sampling_rate(
    wave: NDArray[np.float32], sr_wave: float, query: AudioQuery | FrameAudioQuery
) -> NDArray[np.float32]:
    """音声波形へ音声合成用のクエリがもつ出力サンプリングレート（`outputSamplingRate`）を適用する"""
    # サンプリングレート一致のときはスルー
    if sr_wave == query.outputSamplingRate:
        return wave
    wave = resample(wave, sr_wave, query.outputSamplingRate)
    return wave


def _apply_output_stereo(
    wave: NDArray[np.float32], query: AudioQuery | FrameAudioQuery
) -> NDArray[np.float32]:
    """音声波形へ音声合成用のクエリがもつステレオ出力設定（`outputStereo`）を適用する"""
    if query.outputStereo:
        wave = np.array([wave, wave]).T
    return wave
