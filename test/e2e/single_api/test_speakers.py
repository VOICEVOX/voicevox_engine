"""
/speakers API のテスト
"""

from fastapi.testclient import TestClient


def test_get_speakers_200(client: TestClient) -> None:
    response = client.get("/speakers", params={})
    assert response.status_code == 200
