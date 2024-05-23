"""エンジン取得失敗のテスト"""

from fastapi.testclient import TestClient
from syrupy.assertion import SnapshotAssertion


def test_missing_engine_422(client: TestClient, snapshot_json: SnapshotAssertion) -> None:
    """存在しないエンジンを指定するとエラーを返す。"""
    response = client.post("/audio_query", params={"text": "あ", "speaker": 1, "core_version": "4.0.4"})
    assert response.status_code == 422
    assert snapshot_json == response.json()
