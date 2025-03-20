"""
/core_versions API のテスト
"""

from fastapi.testclient import TestClient
from syrupy.assertion import SnapshotAssertion


def test_get_core_versions_200(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    response = client.get("/core_versions", params={})
    assert response.status_code == 200
    assert snapshot_json == response.json()
