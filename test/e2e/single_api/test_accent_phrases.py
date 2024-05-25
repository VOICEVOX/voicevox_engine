"""
/accent_phrases API のテスト
"""

from test.utility import round_floats

from fastapi.testclient import TestClient
from syrupy.assertion import SnapshotAssertion


def test_post_accent_phrases_200(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    response = client.post(
        "/accent_phrases", params={"text": "テストです", "speaker": 0}
    )
    assert response.status_code == 200
    assert snapshot_json == round_floats(response.json(), 2)
