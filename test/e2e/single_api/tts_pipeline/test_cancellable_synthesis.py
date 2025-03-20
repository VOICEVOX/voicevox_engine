"""
/cancellable_synthesis API のテスト
"""

from test.e2e.single_api.utils import gen_mora
from test.utility import hash_wave_floats_from_wav_bytes

import pytest
from fastapi.testclient import TestClient
from syrupy.assertion import SnapshotAssertion

from voicevox_engine.app.application import generate_app
from voicevox_engine.cancellable_engine import CancellableEngine


@pytest.fixture()
def cancellable_client(app_params: dict) -> TestClient:
    app_params["cancellable_engine"] = CancellableEngine(
        init_processes=1,
        use_gpu=False,
        enable_mock=True,
    )
    cancellable_app = generate_app(**app_params)
    return TestClient(cancellable_app)


def test_post_cancellable_synthesis_200(
    cancellable_client: TestClient, snapshot: SnapshotAssertion
) -> None:
    query = {
        "accent_phrases": [
            {
                "moras": [
                    gen_mora("テ", "t", 2.3, "e", 0.8, 3.3),
                    gen_mora("ス", "s", 2.1, "U", 0.3, 0.0),
                    gen_mora("ト", "t", 2.3, "o", 1.8, 4.1),
                ],
                "accent": 1,
                "pause_mora": None,
                "is_interrogative": False,
            }
        ],
        "speedScale": 1.0,
        "pitchScale": 1.0,
        "intonationScale": 1.0,
        "volumeScale": 1.0,
        "prePhonemeLength": 0.1,
        "postPhonemeLength": 0.1,
        "pauseLength": None,
        "pauseLengthScale": 1.0,
        "outputSamplingRate": 24000,
        "outputStereo": False,
        "kana": "テ'_スト",
    }
    response = cancellable_client.post(
        "/cancellable_synthesis", params={"speaker": 0}, json=query
    )
    assert response.status_code == 200

    # 音声波形が一致する
    assert response.headers["content-type"] == "audio/wav"
    assert snapshot == hash_wave_floats_from_wav_bytes(response.read())


# TODO: キャンセルするテストを追加する
