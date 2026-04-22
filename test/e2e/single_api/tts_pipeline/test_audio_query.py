"""/audio_query API のテスト。"""

import pytest
from fastapi.testclient import TestClient
from syrupy.assertion import SnapshotAssertion

from test.utility import (
    FRAME_DECODE_STYLE_ID,
    NOT_EXIST_STYLE_ID,
    SING_STYLE_ID,
    round_floats,
)


def test_post_audio_query_200(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    response = client.post("/audio_query", params={"text": "テストです", "speaker": 0})
    assert response.status_code == 200
    assert snapshot_json == round_floats(response.json(), round_value=2)


@pytest.mark.parametrize(
    "style_id", [NOT_EXIST_STYLE_ID, FRAME_DECODE_STYLE_ID, SING_STYLE_ID]
)
def test_post_audio_query_with_invalid_style_422(
    client: TestClient, style_id: int, snapshot_json: SnapshotAssertion
) -> None:
    response = client.post(
        "/audio_query", params={"text": "テストです", "speaker": style_id}
    )
    assert response.status_code == 422
    assert snapshot_json == response.json()


def test_post_audio_query_enable_katakana_english_200(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    response = client.post(
        "/audio_query",
        params={"text": "Voivo", "speaker": 0, "enable_katakana_english": True},
    )
    assert response.status_code == 200
    assert snapshot_json == round_floats(response.json(), round_value=2)
