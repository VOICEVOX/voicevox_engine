"""WAVファイルストリームの生成"""

from collections.abc import Generator

import numpy as np


def encode_wave_stream_as_wav(
    wave_length: int,
    wave_generator: Generator[np.ndarray, None, None],
    sampling_rate: int,
    output_stereo: bool,
) -> Generator[bytes, None, None]:
    """Float32の音声ストリームを16bit PCMのWAVファイルストリームに変換する"""
    data_size = wave_length * 2
    file_size = data_size + 44
    channel_size = 2 if output_stereo else 1
    block_size = 16 * channel_size // 8
    block_rate = sampling_rate * block_size
    # WAVファイル冒頭部分（RIFFヘッダ、fmtチャンク、dataチャンクのヘッダ）をyieldする
    yield (
        b"RIFF"
        + (file_size - 8).to_bytes(4, "little")
        + b"WAVEfmt "
        + (16).to_bytes(4, "little")  # fmt header length
        + (1).to_bytes(2, "little")  # PCM
        + channel_size.to_bytes(2, "little")
        + sampling_rate.to_bytes(4, "little")
        + block_rate.to_bytes(4, "little")
        + block_size.to_bytes(2, "little")
        + (16).to_bytes(2, "little")  # bit depth
        + b"data"
        + data_size.to_bytes(4, "little")
    )
    # wave_generatorから生成された音声セグメントを都度16bit PCMに変換してyieldする
    for wave in wave_generator:
        pcm = np.floor(np.clip(wave * 32768, -32768, 32767)).astype("<i2")
        yield pcm.tobytes()
