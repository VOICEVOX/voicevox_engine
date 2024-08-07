"""
/is_initialized_speaker API のテスト
"""

from fastapi.testclient import TestClient
from syrupy.assertion import SnapshotAssertion


def test_get_is_initialized_speaker_200(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    response = client.get("/is_initialized_speaker", params={"speaker": 0})
    assert response.status_code == 200
    assert snapshot_json == response.json()
