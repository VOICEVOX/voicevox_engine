"""
/setting API のテスト
"""

from fastapi.testclient import TestClient
from syrupy.assertion import SnapshotAssertion


def test_get_setting_200(client: TestClient, snapshot: SnapshotAssertion) -> None:
    response = client.get("/setting")
    assert response.status_code == 200
    # HTML string をテスト
    assert snapshot == response.content.decode("utf-8")


def test_post_setting_204(client: TestClient, snapshot: SnapshotAssertion) -> None:
    response = client.post(
        "/setting", data={"cors_policy_mode": "all", "allow_origin": "vv"}
    )
    assert response.status_code == 204
    assert snapshot == response.content
