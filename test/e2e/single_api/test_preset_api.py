"""
プリセットAPIのテスト
"""

from fastapi.testclient import TestClient
from syrupy.assertion import SnapshotAssertion


def test_プリセット一覧を取得できる(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    response = client.get("/presets")
    assert response.status_code == 200
    assert snapshot_json == response.json()
