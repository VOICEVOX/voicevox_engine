"""
/multi_synthesis API のテスト
"""

from test.e2e.single_api.utils import gen_mora

from fastapi.testclient import TestClient


def test_post_multi_synthesis_200(client: TestClient) -> None:
    queries = [
        {
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
        },
        {
            "accent_phrases": [
                {
                    "moras": [
                        gen_mora("テ", "t", 2.3, "e", 0.8, 3.3),
                        gen_mora("ス", "s", 2.1, "U", 0.3, 0.0),
                        gen_mora("ト", "t", 2.3, "o", 1.8, 4.1),
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
            "prePhonemeLength": 0.2,
            "postPhonemeLength": 0.1,
            "outputSamplingRate": 24000,
            "outputStereo": False,
            "kana": "テ'_ストト",
        },
    ]
    response = client.post("/multi_synthesis", params={"speaker": 0}, json=queries)
    assert response.status_code == 200

    # FIXME: ZIP ファイル内の .wav に Linux-Windows 数値精度問題があるため、スナップショットテストには解凍が必要
    assert response.headers["content-type"] == "application/zip"
    # import io
    # from test.utility import hash_long_string, round_floats
    # import soundfile as sf
    # from syrupy.assertion import SnapshotAssertion
    # FileResponse 内の zip ファイルに圧縮された .wav から抽出された音声波形が一致する
    # # zip 解凍
    # waves = concatenate_func(map(lambda path: sf.read(path)[0].tolist(), wave_paths))
    # # NOTE: Linux-Windows 数値精度問題に対するワークアラウンド
    # waves = round_floats(waves, 2)
    # waves_str = " ".join(map(lambda point: str(point), waves))
    # assert snapshot == hash_long_string(waves_str)
