"""
/synthesis API のテスト
"""

from test.e2e.single_api.utils import gen_mora
from test.utility import hash_wave_floats_from_wav_bytes

from fastapi.testclient import TestClient
from syrupy.assertion import SnapshotAssertion


def test_post_synthesis_200(client: TestClient, snapshot: SnapshotAssertion) -> None:
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
    response = client.post("/synthesis", params={"speaker": 0}, json=query)
    assert response.status_code == 200

    # 音声波形が一致する
    assert response.headers["content-type"] == "audio/wav"
    assert snapshot == hash_wave_floats_from_wav_bytes(response.read())


def test_post_synthesis_old_audio_query_200(
    client: TestClient, snapshot: SnapshotAssertion
) -> None:
    """古いバージョンの audio_query でもエラーなく合成できる"""
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
        "outputSamplingRate": 24000,
        "outputStereo": False,
    }
    response = client.post("/synthesis", params={"speaker": 0}, json=query)
    assert response.status_code == 200

    # 音声波形が一致する
    assert response.headers["content-type"] == "audio/wav"
    assert snapshot == hash_wave_floats_from_wav_bytes(response.read())
