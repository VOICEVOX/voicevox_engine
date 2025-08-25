"""/singer_info API のテスト。"""

from fastapi.testclient import TestClient
from syrupy.assertion import SnapshotAssertion

from test.utility import hash_long_string


def test_get_singer_info_200(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    response = client.get(
        "/singer_info", params={"speaker_uuid": "b1a81618-b27b-40d2-b0ea-27a9ad408c4b"}
    )
    assert response.status_code == 200
    assert snapshot_json == hash_long_string(response.json())


def test_get_singer_info_with_url_200(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    response = client.get(
        "/singer_info",
        params={
            "speaker_uuid": "b1a81618-b27b-40d2-b0ea-27a9ad408c4b",
            "resource_format": "url",
        },
    )
    assert response.status_code == 200
    assert snapshot_json == hash_long_string(response.json())


def test_get_singer_info_404(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    response = client.get(
        "/singer_info", params={"speaker_uuid": "111a111a-1a11-1aa1-1a1a-1a11a1aa11a1"}
    )
    assert response.status_code == 404
    assert snapshot_json == hash_long_string(response.json())
