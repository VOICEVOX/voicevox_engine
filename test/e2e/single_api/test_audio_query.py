"""
AudioQuery APIのテスト
"""

from test.utility import round_floats

from fastapi.testclient import TestClient
from syrupy.assertion import SnapshotAssertion


def test_speakerを指定して音声合成クエリが取得できる(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    response = client.post("/audio_query", params={"text": "テストです", "speaker": 0})
    assert response.status_code == 200
    assert snapshot_json == round_floats(response.json(), round_value=2)
