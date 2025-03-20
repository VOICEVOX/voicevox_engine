"""
/morphable_targets API のテスト
"""

from fastapi.testclient import TestClient
from syrupy.assertion import SnapshotAssertion


def test_post_morphable_targets_200(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    response = client.post("/morphable_targets", json=[0])
    assert response.status_code == 200
    assert snapshot_json == response.json()
