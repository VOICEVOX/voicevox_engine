"""
/synthesis API のテスト
"""

from fastapi.testclient import TestClient


def test_post_synthesis_200(client: TestClient) -> None:
    query = {
        'accent_phrases': [
            {'moras': [
                {'text': 'テ', 'consonant': 't', 'consonant_length': 2.3, 'vowel': 'e', 'vowel_length': 0.8, 'pitch': 3.3},
                {'text': 'ス', 'consonant': 's', 'consonant_length': 2.1, 'vowel': 'U', 'vowel_length': 0.3, 'pitch': 0.0},
                {'text': 'ト', 'consonant': 't', 'consonant_length': 2.3, 'vowel': 'o', 'vowel_length': 1.8, 'pitch': 4.1},
            ], 'accent': 1, 'pause_mora': None, 'is_interrogative': False}
        ],
       'speedScale': 1.0,
       'pitchScale': 1.0,
       'intonationScale': 1.0,
       'volumeScale': 1.0,
       'prePhonemeLength': 0.1,
       'postPhonemeLength': 0.1,
       'outputSamplingRate': 24000,
       'outputStereo': False,
       'kana': "テ'_スト"
    }
    response = client.post("/synthesis", params={"speaker": 0}, json=query)
    assert response.status_code == 200

