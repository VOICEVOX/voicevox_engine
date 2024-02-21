"""
setting APIのテスト
"""

from fastapi.testclient import TestClient
from syrupy.assertion import SnapshotAssertion


def test_setting画面が取得できる(client: TestClient, snapshot: SnapshotAssertion) -> None:
    response = client.get("/setting")
    assert response.status_code == 200
    assert snapshot == response.content.decode("utf-8")
