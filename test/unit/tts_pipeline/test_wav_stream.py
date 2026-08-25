"""wav_stream 関数の単体テスト。"""

import io
from collections.abc import Iterator

import numpy as np
import numpy.testing
import soundfile
from numpy.typing import NDArray

from voicevox_engine.tts_pipeline.wav_stream import (
    encode_wave_stream_as_wav,
)


def _generate_sine_wave_ndarray(
    seconds: float, samplerate: int, frequency: float
) -> NDArray[np.float32]:
    x = np.linspace(0, seconds, int(seconds * samplerate), endpoint=False)
    wave: NDArray[np.float32] = np.sin(2 * np.pi * frequency * x).astype(np.float32)

    return wave


def segment_generator(
    wave: NDArray[np.float32], segment_size: int
) -> Iterator[NDArray[np.float32]]:
    for i in range(0, len(wave), segment_size):
        yield wave[i : i + segment_size]


def test_encode() -> None:
    # Inputs
    wave = _generate_sine_wave_ndarray(seconds=2, samplerate=16000, frequency=100)
    wave_generator = segment_generator(wave, segment_size=1000)

    # Outputs
    wavfile_generator = encode_wave_stream_as_wav(
        wave_length=len(wave),
        wave_generator=wave_generator,
        sampling_rate=16000,
        output_stereo=False,
    )
    wavfile_bio = io.BytesIO()
    for segment in wavfile_generator:
        wavfile_bio.write(segment)
    wavfile_bio.seek(0)
    wave_decoded, samplerate_decoded = soundfile.read(wavfile_bio, dtype="float32")

    # Test
    assert samplerate_decoded == 16000
    assert wave_decoded.shape == wave.shape
    numpy.testing.assert_allclose(
        wave_decoded, wave, rtol=0, atol=1 / 32768
    )  # NOTE: 1/32768はPCM16へのfloor量子化で生じる誤差の上限
