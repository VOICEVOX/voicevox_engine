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
    """生音声波形ストリームにクエリを適用して出力音声波形を生成し、サンプル数とストリームを返す"""
    # TODO: 大半の処理が`raw_wave_to_output_wave()`と同じなので共通化する
    output_rate = query.outputSamplingRate
    wave_length = (raw_wave_length * output_rate + sr_wave // 2) // sr_wave

    stream = map(lambda wave: _apply_volume_scale(wave, query), stream)
    stream = _apply_output_sampling_rate_stream(stream, sr_wave, query)
    stream = map(lambda wave: _apply_output_stereo(wave, query), stream)

    return wave_length, stream


def _apply_output_sampling_rate_stream(
    stream: Iterator[NDArray[np.float32]],
    sr_wave: float,
    query: AudioQuery | FrameAudioQuery,
) -> Iterator[NDArray[np.float32]]:
    """音声波形ストリームへ音声合成用のクエリがもつ出力サンプリングレート（`outputSamplingRate`）を適用する"""
    if sr_wave == query.outputSamplingRate:
        yield from stream
        return

    resampler = ResampleStream(sr_wave, query.outputSamplingRate, 1)
    yield from map(resampler.resample_chunk, stream)

    # NOTE: 最後の出力を空配列でフラッシュする
    yield resampler.resample_chunk(np.empty(0, dtype=np.float32), True)


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
