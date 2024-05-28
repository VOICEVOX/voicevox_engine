"""
/add_preset API のテスト
"""

from fastapi.testclient import TestClient
from syrupy.assertion import SnapshotAssertion


def test_post_add_preset_200(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    preset = {
        "id": 9999,
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
    response = client.post("/add_preset", params={}, json=preset)
    assert response.status_code == 200
    assert snapshot_json == response.json()
