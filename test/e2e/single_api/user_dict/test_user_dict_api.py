"""
/user_dict API のテスト
"""

from fastapi.testclient import TestClient
from syrupy.assertion import SnapshotAssertion


def test_get_user_dict_200(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    response = client.get("/user_dict", params={})
    assert response.status_code == 200
    assert snapshot_json == response.json()
