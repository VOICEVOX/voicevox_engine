"""
/version API のテスト
"""

from fastapi.testclient import TestClient
from syrupy.assertion import SnapshotAssertion


def test_get_version_200(client: TestClient, snapshot_json: SnapshotAssertion) -> None:
    response = client.get("/version", params={})
    assert response.status_code == 200
    assert snapshot_json == response.json()
