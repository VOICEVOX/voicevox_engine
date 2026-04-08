"""/initialize_speaker API のテスト。"""

from fastapi.testclient import TestClient
from syrupy.assertion import SnapshotAssertion


def test_post_initialize_speaker_204(
    client: TestClient, snapshot: SnapshotAssertion
) -> None:
    response = client.post("/initialize_speaker", params={"speaker": 0})
    assert response.status_code == 204
    assert snapshot == response.content


def test_post_initialize_speaker_with_not_exist_id_422(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    response = client.post("/initialize_speaker", params={"speaker": -1024})
    assert response.status_code == 422
    assert snapshot_json == response.json()
