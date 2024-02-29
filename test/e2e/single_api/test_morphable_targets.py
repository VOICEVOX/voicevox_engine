"""
/morphable_targets API のテスト
"""

from fastapi.testclient import TestClient


def test_post_morphable_targets_200(client: TestClient) -> None:
    response = client.post("/morphable_targets", json=[0])
    assert response.status_code == 200
