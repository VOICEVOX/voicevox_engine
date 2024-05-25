"""
/supported_devices API のテスト
"""

from fastapi.testclient import TestClient
from syrupy.assertion import SnapshotAssertion


def test_get_supported_devices_200(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    response = client.get("/supported_devices", params={})
    assert response.status_code == 200
    assert snapshot_json == response.json()
