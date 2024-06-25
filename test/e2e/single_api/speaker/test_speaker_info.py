"""
/speaker_info API のテスト
"""

from test.utility import hash_long_string

from fastapi.testclient import TestClient
from syrupy.assertion import SnapshotAssertion


def test_get_speaker_info_200(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    response = client.get(
        "/speaker_info", params={"speaker_uuid": "388f246b-8c41-4ac1-8e2d-5d79f3ff56d9"}
    )
    assert response.status_code == 200
    assert snapshot_json == hash_long_string(response.json())


def test_get_singer_info_with_url_200(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    response = client.get(
        "/speaker_info",
        params={
            "speaker_uuid": "388f246b-8c41-4ac1-8e2d-5d79f3ff56d9",
            "resource_format": "url",
        },
    )
    assert response.status_code == 200
    assert snapshot_json == hash_long_string(response.json())
