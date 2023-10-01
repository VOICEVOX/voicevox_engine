import base64
import io
from unittest import TestCase

import numpy as np
import numpy.testing
import soundfile
from soxr import resample

from voicevox_engine.utility import ConnectBase64WavesException, connect_base64_waves


def generate_sine_wave_ndarray(
    seconds: float, samplerate: int, frequency: float
) -> np.ndarray:
    x = np.linspace(0, seconds, int(seconds * samplerate), endpoint=False)
    wave = np.sin(2 * np.pi * frequency * x).astype(np.float32)

    return wave


def encode_bytes(wave_ndarray: np.ndarray, samplerate: int) -> bytes:
    wave_bio = io.BytesIO()
    soundfile.write(
        file=wave_bio,
        data=wave_ndarray,
        samplerate=samplerate,
        format="WAV",
        subtype="FLOAT",
    )
    wave_bio.seek(0)

    return wave_bio.getvalue()


def generate_sine_wave_bytes(
    seconds: float, samplerate: int, frequency: float
) -> bytes:
    wave_ndarray = generate_sine_wave_ndarray(seconds, samplerate, frequency)
    return encode_bytes(wave_ndarray, samplerate)


def encode_base64(wave_bytes: bytes) -> str:
    return base64.standard_b64encode(wave_bytes).decode("utf-8")


def generate_sine_wave_base64(seconds: float, samplerate: int, frequency: float) -> str:
    wave_bytes = generate_sine_wave_bytes(seconds, samplerate, frequency)
    wave_base64 = encode_base64(wave_bytes)
    return wave_base64


class TestConnectBase64Waves(TestCase):
    def test_connect(self):
        samplerate = 1000
        wave = generate_sine_wave_ndarray(
            seconds=2, samplerate=samplerate, frequency=10
        )
        wave_base64 = encode_base64(encode_bytes(wave, samplerate=samplerate))

        wave_x2_ref = np.concatenate([wave, wave])

        wave_x2, _ = connect_base64_waves(waves=[wave_base64, wave_base64])

        self.assertEqual(wave_x2_ref.shape, wave_x2.shape)

        self.assertTrue((wave_x2_ref == wave_x2).all())

    def test_no_wave_error(self):
        self.assertRaises(ConnectBase64WavesException, connect_base64_waves, waves=[])

    def test_invalid_base64_error(self):
        wave_1000hz = generate_sine_wave_base64(
            seconds=2, samplerate=1000, frequency=10
        )
        wave_1000hz_broken = wave_1000hz[1:]  # remove head 1 char

        self.assertRaises(
            ConnectBase64WavesException,
            connect_base64_waves,
            waves=[
                wave_1000hz_broken,
            ],
        )

    def test_invalid_wave_file_error(self):
        wave_1000hz = generate_sine_wave_bytes(seconds=2, samplerate=1000, frequency=10)
        wave_1000hz_broken_bytes = wave_1000hz[1:]  # remove head 1 byte
        wave_1000hz_broken = encode_base64(wave_1000hz_broken_bytes)

        self.assertRaises(
            ConnectBase64WavesException,
            connect_base64_waves,
            waves=[
                wave_1000hz_broken,
            ],
        )

    def test_different_frequency(self):
        wave_24000hz = generate_sine_wave_ndarray(
            seconds=1, samplerate=24000, frequency=10
        )
        wave_1000hz = generate_sine_wave_ndarray(
            seconds=2, samplerate=1000, frequency=10
        )
        wave_24000_base64 = encode_base64(encode_bytes(wave_24000hz, samplerate=24000))
        wave_1000_base64 = encode_base64(encode_bytes(wave_1000hz, samplerate=1000))

        wave_1000hz_to24000hz = resample(wave_1000hz, 1000, 24000)
        wave_x2_ref = np.concatenate([wave_24000hz, wave_1000hz_to24000hz])

        wave_x2, _ = connect_base64_waves(waves=[wave_24000_base64, wave_1000_base64])

        self.assertEqual(wave_x2_ref.shape, wave_x2.shape)
        numpy.testing.assert_array_almost_equal(wave_x2_ref, wave_x2)

    def test_different_channels(self):
        wave_1000hz = generate_sine_wave_ndarray(
            seconds=2, samplerate=1000, frequency=10
        )
        wave_2ch_1000hz = np.array([wave_1000hz, wave_1000hz]).T
        wave_1ch_base64 = encode_base64(encode_bytes(wave_1000hz, samplerate=1000))
        wave_2ch_base64 = encode_base64(encode_bytes(wave_2ch_1000hz, samplerate=1000))

        wave_x2_ref = np.concatenate([wave_2ch_1000hz, wave_2ch_1000hz])

        wave_x2, _ = connect_base64_waves(waves=[wave_1ch_base64, wave_2ch_base64])

        self.assertEqual(wave_x2_ref.shape, wave_x2.shape)
        self.assertTrue((wave_x2_ref == wave_x2).all())
