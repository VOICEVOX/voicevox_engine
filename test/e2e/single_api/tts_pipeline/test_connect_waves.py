"""
/connect_waves API のテスト
"""

import base64
from pathlib import Path

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
