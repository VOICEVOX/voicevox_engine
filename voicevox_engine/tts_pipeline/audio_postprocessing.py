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
    frame_length: int,
    stream: Iterator[NDArray[np.float32]],
    sr_wave: int,
) -> tuple[int, Iterator[NDArray[np.float32]]]:
    """生音声波形に音声合成用のクエリを適用して出力音声波形を生成する(ストリーミング用)"""
    wave_length = frame_length
    output_rate = query.outputSamplingRate

    if sr_wave != output_rate:
        # NOTE: 正確な計算式は不明
        wave_length = round(frame_length * output_rate / sr_wave)

    def volume_scale(
        stream: Iterator[NDArray[np.float32]],
    ) -> Iterator[NDArray[np.float32]]:
        for wave in stream:
            yield _apply_volume_scale(wave, query)

    def resample(
        stream: Iterator[NDArray[np.float32]],
    ) -> Iterator[NDArray[np.float32]]:
        # サンプリングレート一致のときはスルー
        if sr_wave == query.outputSamplingRate:
            yield from stream
            return
        # ResampleStreamには最後の入力を明示する必要があるので予め取り出しておく
        buffer = next(stream)
        resampler = ResampleStream(
            sr_wave, query.outputSamplingRate, buffer.ndim, buffer.dtype
        )

        remmend_length = wave_length
        for raw_wave in stream:
            chunk = resampler.resample_chunk(buffer)
            chunk_length = len(chunk)
            if chunk_length >= remmend_length:
                # 計算したリサンプリング後の長さが実際より大幅に短かった場合
                yield chunk[0:remmend_length]
                return
            remmend_length -= chunk_length
            buffer = raw_wave
            yield chunk

        last_chunk = resampler.resample_chunk(buffer, True)
        last_chunk_length = len(last_chunk)
        # 事前に計算したリサンプリング後の長さに誤差があった場合、事前に計算した長さに合わせる
        if last_chunk_length < remmend_length:
            yield np.pad(last_chunk, (0, remmend_length - last_chunk_length), "edge")
        elif last_chunk_length > remmend_length:
            yield last_chunk[0:remmend_length]
        else:
            yield last_chunk

    def output_stereo(
        stream: Iterator[NDArray[np.float32]],
    ) -> Iterator[NDArray[np.float32]]:
        for wave in stream:
            yield _apply_output_stereo(wave, query)

    return wave_length, output_stereo(resample(volume_scale(stream)))


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
