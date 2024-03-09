"""
/version API のテスト
"""

from fastapi.testclient import TestClient


def test_get_version_200(client: TestClient) -> None:
    response = client.get("/version", params={})
    assert response.status_code == 200
