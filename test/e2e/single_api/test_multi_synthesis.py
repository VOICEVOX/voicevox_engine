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
