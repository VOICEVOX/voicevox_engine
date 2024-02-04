from fastapi.testclient import TestClient
from syrupy.assertion import SnapshotAssertion


def test_fetch_speakers_success(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    response = client.get("/speakers")
    assert response.status_code == 200
    assert snapshot_json == response.json()
