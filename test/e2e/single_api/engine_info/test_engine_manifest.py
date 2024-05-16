"""
/engine_manifest API のテスト
"""

from test.utility import hash_long_string

from fastapi.testclient import TestClient
from syrupy.assertion import SnapshotAssertion


def test_get_engine_manifest_200(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    response = client.get("/engine_manifest")
    assert response.status_code == 200
    assert snapshot_json == hash_long_string(response.json())
