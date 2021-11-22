from unittest import TestCase

import io
import base64

import numpy as np
import soundfile

from voicevox_engine.util import connect_base64_waves, ConnectBase64WavesException


def generate_sine_wave_bytes(seconds: float, samplerate: int, frequency: float) -> bytes:
    x = np.linspace(0, seconds, int(seconds * samplerate), endpoint=False)
    wave = np.sin(2 * np.pi * frequency * x)

    wave_bio = io.BytesIO()
    soundfile.write(
        file=wave_bio, data=wave, samplerate=samplerate, format="WAV"
    )
    wave_bio.seek(0)

    return wave_bio.getvalue()

def encode_base64(wave_bytes: bytes) -> str:
    return base64.standard_b64encode(wave_bytes)

def generate_sine_wave_base64(seconds: float, samplerate: int, frequency: float) -> str:
    wave_bytes = generate_sine_wave_bytes(seconds, samplerate, frequency)
    wave_base64 = encode_base64(wave_bytes)
    return wave_base64


class TestConnectBase64Waves(TestCase):
    def test_no_wave_error(self):
        self.assertRaises(ConnectBase64WavesException, connect_base64_waves, waves=[])

    def test_invalid_base64_error(self):
        wave_1000hz = generate_sine_wave_base64(seconds=2, samplerate=1000, frequency=10)
        wave_1000hz_broken = wave_1000hz[1:]  # strip head 1 char

        self.assertRaises(ConnectBase64WavesException, connect_base64_waves, waves=[
            wave_1000hz_broken,
        ])

    def test_invalid_wave_error(self):
        wave_1000hz = generate_sine_wave_bytes(seconds=2, samplerate=1000, frequency=10)
        wave_1000hz_broken = wave_1000hz[1:]  # strip head 1 byte
        wave_1000hz_broken_base64 = encode_base64(wave_1000hz_broken)

        self.assertRaises(ConnectBase64WavesException, connect_base64_waves, waves=[
            wave_1000hz_broken_base64,
        ])

    def test_different_frequency_error(self):
        wave_24000hz = generate_sine_wave_base64(seconds=1, samplerate=24000, frequency=10)
        wave_1000hz = generate_sine_wave_base64(seconds=2, samplerate=1000, frequency=10)

        self.assertRaises(ConnectBase64WavesException, connect_base64_waves, waves=[
            wave_24000hz,
            wave_1000hz,
        ])
