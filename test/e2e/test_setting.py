"""
setting APIのテスト
"""

from fastapi.testclient import TestClient
from syrupy.assertion import SnapshotAssertion


def test_setting画面が取得できる(client: TestClient, snapshot_json: SnapshotAssertion) -> None:
    response = client.get("/setting")
    assert response.status_code == 200
    print(response.content)
    assert snapshot_json == response.content
