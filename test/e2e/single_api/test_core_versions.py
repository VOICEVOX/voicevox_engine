"""
/core_versions API のテスト
"""

from fastapi.testclient import TestClient


def test_get_core_versions_200(client: TestClient) -> None:
    response = client.get("/core_versions", params={})
    assert response.status_code == 200
