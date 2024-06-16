"""
/audio_query_from_preset API のテスト
"""

from test.utility import round_floats

from fastapi.testclient import TestClient
from syrupy.assertion import SnapshotAssertion


def test_post_audio_query_from_preset_200(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    # Setup
    # NOTE: 事前準備用のプリセット API が壊れた場合、このテストが偽陽性で failed になる可能性がある
    preset = {
        "id": 8888,
        "name": "test_preset",
        "speaker_uuid": "123-456-789-234",
        "style_id": 9999,
        "speedScale": 1.1,
        "pitchScale": 0.9,
        "intonationScale": 1.2,
        "volumeScale": 1.3,
        "prePhonemeLength": 20,
        "postPhonemeLength": 5,
        "pauseLength": 15,
        "pauseLengthScale": 1.4,
    }
    client.post("/add_preset", params={}, json=preset)

    # Test
    response = client.post(
        "/audio_query_from_preset", params={"text": "テストです", "preset_id": 8888}
    )
    assert response.status_code == 200
    assert snapshot_json == round_floats(response.json(), 2)


def test_post_audio_query_from_preset_422(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    response = client.post(
        "/audio_query_from_preset", params={"text": "テストです", "preset_id": 404}
    )
    assert response.status_code == 422
    assert snapshot_json == response.json()
