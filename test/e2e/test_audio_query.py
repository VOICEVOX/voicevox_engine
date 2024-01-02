"""
AudioQuery APIのテスト
"""

from fastapi.testclient import TestClient
from syrupy.extensions.json import JSONSnapshotExtension


def test_style_idを指定して音声合成クエリが取得できる(
    client: TestClient, snapshot_json: JSONSnapshotExtension
) -> None:
    response = client.post("/audio_query", params={"text": "テストです", "style_id": 0})
    assert response.status_code == 200
    assert snapshot_json == response.json()


def test_speakerを指定しても音声合成クエリが取得できる(
    client: TestClient, snapshot_json: JSONSnapshotExtension
) -> None:
    response = client.post("/audio_query", params={"text": "テストです", "speaker": 0})
    assert response.status_code == 200
    assert snapshot_json == response.json()


def test_style_idとspeakerを両方指定するとエラー(client: TestClient) -> None:
    response = client.post(
        "/audio_query", params={"text": "テストです", "style_id": 0, "speaker": 0}
    )
    assert response.status_code == 400
