"""入力値の範囲検証のテスト。"""

from typing import Any

from fastapi.testclient import TestClient

from test.e2e.single_api.utils import gen_mora


def _gen_audio_query() -> dict[str, Any]:
    """有効な音声合成用クエリを生成する。"""
    return {
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


def _gen_preset() -> dict[str, Any]:
    """有効なプリセットを生成する。"""
    return {
        "id": 9999,
        "name": "test_preset",
        "speaker_uuid": "123-456-789-234",
        "style_id": 9999,
        "speedScale": 1.0,
        "pitchScale": 1.0,
        "intonationScale": 1.0,
        "volumeScale": 1.0,
        "prePhonemeLength": 0.1,
        "postPhonemeLength": 0.1,
        "pauseLength": None,
        "pauseLengthScale": 1.0,
    }


def test_audio_query_ranges_422(client: TestClient) -> None:
    """音声合成用クエリの範囲外の値を拒否する。"""
    invalid_values = {
        "speedScale": 0,
        "prePhonemeLength": -1,
        "postPhonemeLength": -1,
        "pauseLength": -1,
        "pauseLengthScale": -1,
        "outputSamplingRate": 0,
    }
    for field, value in invalid_values.items():
        query = _gen_audio_query()
        query[field] = value
        response = client.post("/synthesis", params={"speaker": 0}, json=query)
        assert response.status_code == 422


def test_mora_and_accent_phrase_ranges_422(client: TestClient) -> None:
    """モーラとアクセント句の範囲外の値を拒否する。"""
    invalid_queries = []
    query = _gen_audio_query()
    query["accent_phrases"][0]["moras"][0]["vowel_length"] = -1
    invalid_queries.append(query)

    query = _gen_audio_query()
    query["accent_phrases"][0]["moras"][0]["consonant_length"] = -1
    invalid_queries.append(query)

    query = _gen_audio_query()
    query["accent_phrases"][0]["accent"] = 0
    invalid_queries.append(query)

    query = _gen_audio_query()
    query["accent_phrases"][0]["accent"] = 4
    invalid_queries.append(query)

    for query in invalid_queries:
        response = client.post("/synthesis", params={"speaker": 0}, json=query)
        assert response.status_code == 422


def test_preset_ranges_422(client: TestClient) -> None:
    """プリセットの範囲外の値を拒否する。"""
    invalid_values = {
        "speedScale": 0,
        "prePhonemeLength": -1,
        "postPhonemeLength": -1,
        "pauseLength": -1,
        "pauseLengthScale": -1,
    }
    for field, value in invalid_values.items():
        preset = _gen_preset()
        preset[field] = value
        response = client.post("/add_preset", json=preset)
        assert response.status_code == 422


def test_streaming_synthesis_ranges_422(client: TestClient) -> None:
    """ストリーミング音声合成の範囲外の値を拒否する。"""
    query = _gen_audio_query()
    for field, value in {"start_offset": -1, "segment_length": 0}.items():
        response = client.post(
            "/streaming_synthesis",
            params={"speaker": 0, field: value},
            json=query,
        )
        assert response.status_code == 422
