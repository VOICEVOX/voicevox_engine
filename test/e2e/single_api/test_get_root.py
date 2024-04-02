"""
/ API のテスト
"""

from fastapi.testclient import TestClient
from syrupy.assertion import SnapshotAssertion


def test_get_root_200(client: TestClient, snapshot: SnapshotAssertion) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert snapshot == response.content.decode("utf-8")
