"""
/update_preset API のテスト
"""

from fastapi.testclient import TestClient
from syrupy.assertion import SnapshotAssertion


def test_post_update_preset_200(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    preset = {
        "id": 1,
        "name": "test_preset",
        "speaker_uuid": "123-456-789-234",
        "style_id": 9999,
        "speedScale": 1,
        "pitchScale": 1,
        "intonationScale": 1,
        "volumeScale": 1,
        "prePhonemeLength": 10,
        "postPhonemeLength": 10,
        "pauseLength": None,
        "pauseLengthScale": 1,
    }
    response = client.post("/update_preset", params={}, json=preset)
    assert response.status_code == 200
    assert snapshot_json == response.json()


def test_post_update_preset_422(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    preset = {
        "id": 4040000000,
        "name": "Nessie",
        "speaker_uuid": "404-404-404-404",
        "style_id": 404,
        "speedScale": 404,
        "pitchScale": 404,
        "intonationScale": 404,
        "volumeScale": 404,
        "prePhonemeLength": 404,
        "postPhonemeLength": 404,
        "pauseLength": 404,
        "pauseLengthScale": 404,
    }
    response = client.post("/update_preset", params={}, json=preset)
    assert response.status_code == 422
    assert snapshot_json == response.json()
