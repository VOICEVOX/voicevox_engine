"""
/connect_waves API のテスト
"""

import base64
from pathlib import Path
from test.utility import hash_wave_floats_from_wav_bytes

from fastapi.testclient import TestClient
from syrupy.assertion import SnapshotAssertion


def test_post_connect_waves_200(
    client: TestClient, snapshot: SnapshotAssertion
) -> None:
    wavs = [
        base64.b64encode(
            Path("test/e2e/single_api/tts_pipeline/test_audio/sample1.wav").read_bytes()
        ).decode(),
        base64.b64encode(
            Path("test/e2e/single_api/tts_pipeline/test_audio/sample2.wav").read_bytes()
        ).decode(),
    ]

    response = client.post("/connect_waves", json=wavs)
    assert response.status_code == 200

    # 音声波形が一致する
    assert response.headers["content-type"] == "audio/wav"
    assert snapshot == hash_wave_floats_from_wav_bytes(response.read())
