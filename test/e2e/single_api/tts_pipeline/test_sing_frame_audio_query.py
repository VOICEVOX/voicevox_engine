"""/sing_frame_audio_query API のテスト。"""

import pytest
from fastapi.testclient import TestClient
from syrupy.assertion import SnapshotAssertion

from test.utility import (
    FRAME_DECODE_STYLE_ID,
    NOT_EXIST_STYLE_ID,
    TALK_STYLE_ID,
    round_floats,
)

_score = {
    "notes": [
        {"id": "a", "key": None, "frame_length": 10, "lyric": ""},
        {"id": "b", "key": 30, "frame_length": 3, "lyric": "て"},
        {"id": "c", "key": 30, "frame_length": 3, "lyric": "す"},
        {"id": "d", "key": 40, "frame_length": 1, "lyric": "と"},
        {"id": "e", "key": None, "frame_length": 10, "lyric": ""},
    ]
}


def test_post_sing_frame_audio_query_200(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    response = client.post(
        "/sing_frame_audio_query", params={"speaker": 7}, json=_score
    )
    assert response.status_code == 200
    assert snapshot_json == round_floats(response.json(), 2)


@pytest.mark.parametrize(
    "style_id", [NOT_EXIST_STYLE_ID, TALK_STYLE_ID, FRAME_DECODE_STYLE_ID]
)
def test_post_sing_frame_audio_query_with_invalid_style_422(
    client: TestClient, style_id: int, snapshot_json: SnapshotAssertion
) -> None:
    response = client.post(
        "/sing_frame_audio_query", params={"speaker": style_id}, json=_score
    )
    assert response.status_code == 422
    assert snapshot_json == response.json()


def test_post_sing_old_frame_audio_query_200(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    """古いバージョンの楽譜でもエラーなく合成できる"""
    score = {
        "notes": [
            {"key": None, "frame_length": 10, "lyric": ""},
            {"key": 30, "frame_length": 3, "lyric": "て"},
            {"key": 30, "frame_length": 3, "lyric": "す"},
            {"key": 40, "frame_length": 1, "lyric": "と"},
            {"key": None, "frame_length": 10, "lyric": ""},
        ]
    }
    response = client.post("/sing_frame_audio_query", params={"speaker": 7}, json=score)
    assert response.status_code == 200
    assert snapshot_json == round_floats(response.json(), 2)
