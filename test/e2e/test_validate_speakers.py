from fastapi.testclient import TestClient
from syrupy.extensions.json import JSONSnapshotExtension


def test_fetch_speakers_success(
    client: TestClient, snapshot_json: JSONSnapshotExtension
) -> None:
    response = client.get("/speakers")
    assert response.status_code == 200
    assert snapshot_json == response.json()
