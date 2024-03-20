"""
/initialize_speaker API のテスト
"""

from fastapi.testclient import TestClient


def test_post_initialize_speaker_204(client: TestClient) -> None:
    response = client.post("/initialize_speaker", params={"speaker": 0})
    assert response.status_code == 204
