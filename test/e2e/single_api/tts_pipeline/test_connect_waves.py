"""/connect_waves API のテスト。"""

import base64
import io
from pathlib import Path

import numpy as np
import soundfile
from fastapi.testclient import TestClient
from syrupy.assertion import SnapshotAssertion

from test.utility import hash_wave_floats_from_wav_bytes


def test_post_connect_waves_200(
    client: TestClient, snapshot: SnapshotAssertion
) -> None:
    test_audio_dir = Path(__file__).parent / "test_audio"
    wavs = [
        base64.b64encode((test_audio_dir / "sample1.wav").read_bytes()).decode(),
        base64.b64encode((test_audio_dir / "sample2.wav").read_bytes()).decode(),
    ]

    response = client.post("/connect_waves", json=wavs)
    assert response.status_code == 200

    # 音声波形が一致する
    assert response.headers["content-type"] == "audio/wav"
    assert snapshot == hash_wave_floats_from_wav_bytes(response.read())


def test_post_connect_waves_422(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    wavs: list[None] = []

    response = client.post("/connect_waves", json=wavs)

    assert response.status_code == 422
    assert snapshot_json == response.json()


def test_post_connect_waves_invalid_channels_422(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    wavs = []
    for data in [
        np.zeros(1, dtype=np.float32),
        np.zeros((1, 3), dtype=np.float32),
    ]:
        wave = io.BytesIO()
        soundfile.write(
            file=wave,
            data=data,
            samplerate=24000,
            format="WAV",
        )
        wavs.append(base64.b64encode(wave.getvalue()).decode())

    response = client.post("/connect_waves", json=wavs)

    assert response.status_code == 422
    assert snapshot_json == response.json()
