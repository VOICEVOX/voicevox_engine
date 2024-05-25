"""
/speaker_info API のテスト
"""

from fastapi.testclient import TestClient


def test_get_speaker_info_200(client: TestClient) -> None:
    response = client.get(
        "/speaker_info", params={"speaker_uuid": "388f246b-8c41-4ac1-8e2d-5d79f3ff56d9"}
    )
    assert response.status_code == 200
