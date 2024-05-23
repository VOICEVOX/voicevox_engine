"""
/presets API のテスト
"""

from fastapi.testclient import TestClient
from syrupy.assertion import SnapshotAssertion


def test_get_presets_200(client: TestClient, snapshot_json: SnapshotAssertion) -> None:
    response = client.get("/presets")
    print('snapshot', snapshot_json)
    print('response', response.json())
    assert response.status_code == 200
    assert snapshot_json == response.json()
