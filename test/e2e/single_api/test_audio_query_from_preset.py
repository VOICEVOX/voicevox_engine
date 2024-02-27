"""
/audio_query_from_preset API のテスト
"""

from fastapi.testclient import TestClient


# def test_post_audio_query_from_preset_200(client: TestClient) -> None:
#     response = client.post("/audio_query_from_preset", params={"text": "テストです", "preset_id": 0})
#     assert response.status_code == 200


def test_post_audio_query_from_preset_422(client: TestClient) -> None:
    response = client.post("/audio_query_from_preset", params={"text": "テストです", "preset_id": 404})
    assert response.status_code == 422
