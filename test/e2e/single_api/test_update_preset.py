"""
/update_preset API のテスト
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.skip(reason="プリセット変更が他のテストに干渉するから")
def test_post_update_preset_200(client: TestClient) -> None:
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
    }
    response = client.post("/update_preset", params={}, json=preset)
    assert response.status_code == 200
