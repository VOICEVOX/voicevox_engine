"""コア取得失敗のテスト"""

from fastapi.testclient import TestClient
from syrupy.assertion import SnapshotAssertion


def test_missing_core_422(client: TestClient, snapshot_json: SnapshotAssertion) -> None:
    """存在しないコアを指定するとエラーを返す。"""
    response = client.get("/speakers", params={"core_version": "4.0.4"})
    assert response.status_code == 422
    assert snapshot_json == response.json()
