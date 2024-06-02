"""
/initialize_speaker API のテスト
"""

from fastapi.testclient import TestClient
from syrupy.assertion import SnapshotAssertion


def test_post_initialize_speaker_204(
    client: TestClient, snapshot: SnapshotAssertion
) -> None:
    response = client.post("/initialize_speaker", params={"speaker": 0})
    assert response.status_code == 204
    assert snapshot == response.content
