"""
/synthesis_morphing API のテスト
"""

from test.e2e.single_api.utils import gen_mora

from fastapi.testclient import TestClient


def test_post_synthesis_morphing_200(client: TestClient) -> None:
    queries = {
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
        "kana": "テ'_スト",
    }
    response = client.post(
        "/synthesis_morphing",
        params={"base_speaker": 0, "target_speaker": 0, "morph_rate": 0.8},
        json=queries,
    )
    assert response.status_code == 200

    # FIXME: Linux-MacOS 計算結果不一致問題によりスナップショットテストがコケる
    # import io
    # from test.utility import hash_long_string, round_floats
    # import soundfile as sf
    # from syrupy.assertion import SnapshotAssertion
    # # FileResponse 内の .wav から抽出された音声波形が一致する
    # assert response.headers["content-type"] == "audio/wav"
    # wave = sf.read(io.BytesIO(response.read()))[0].tolist()
    # # NOTE: Linux-Windows 数値精度問題に対するワークアラウンド
    # wave = round_floats(wave, 2)
    # wave_str = " ".join(map(lambda point: str(point), wave))
    # assert snapshot == hash_long_string(wave_str)
