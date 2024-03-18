"""
/audio_query_from_preset API のテスト
"""

from test.utility import round_floats

import pytest
from fastapi.testclient import TestClient
from syrupy.assertion import SnapshotAssertion


@pytest.mark.skip(reason="200の前提として別APIを要するプリセット登録が必要だから")
def test_post_audio_query_from_preset_200(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    response = client.post(
        "/audio_query_from_preset", params={"text": "テストです", "preset_id": 0}
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
