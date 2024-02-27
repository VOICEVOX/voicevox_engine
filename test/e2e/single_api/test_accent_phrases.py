"""
/accent_phrases API のテスト
"""

from fastapi.testclient import TestClient


def test_post_accent_phrases_200(client: TestClient) -> None:
    response = client.post("/accent_phrases", params={"text": "テストです", "speaker": 0})
    assert response.status_code == 200
