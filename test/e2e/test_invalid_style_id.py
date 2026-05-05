"""不適切なStyleIDを渡した場合のテスト"""

import pytest
from fastapi.testclient import TestClient
from syrupy.assertion import SnapshotAssertion

from test.utility import (
    FRAME_DECODE_STYLE_ID,
    NOT_EXIST_STYLE_ID,
    SING_STYLE_ID,
    TALK_STYLE_ID,
)


@pytest.mark.parametrize(
    "style_id", [NOT_EXIST_STYLE_ID, FRAME_DECODE_STYLE_ID, SING_STYLE_ID]
)
def test_accent_phrases_with_invalid_style_422(
    client: TestClient, style_id: int, snapshot_json: SnapshotAssertion
) -> None:
    response = client.post(
        "/accent_phrases", params={"text": "テストです", "speaker": style_id}
    )
    assert response.status_code == 422
    assert snapshot_json == response.json()


@pytest.mark.parametrize("style_id", [NOT_EXIST_STYLE_ID, TALK_STYLE_ID])
def test_frame_synthesis_with_invalid_style_422(
    client: TestClient, style_id: int, snapshot_json: SnapshotAssertion
) -> None:
    query = {
        "f0": [
            0.0,
            0.0,
            46.63821792602539,
            46.63821792602539,
            46.63821792602539,
            46.63821792602539,
            46.63821792602539,
            46.63821792602539,
            46.63821792602539,
            46.63821792602539,
            46.396461486816406,
            46.396461486816406,
            46.61719512939453,
            46.66975021362305,
            83.099853515625,
            83.099853515625,
            82.96875762939453,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
        ],
        "volume": [
            0.0,
            0.0,
            0.3342486023902893,
            0.3342486023902893,
            0.3342486023902893,
            0.3342486023902893,
            0.3342486023902893,
            0.3342486023902893,
            0.3342486023902893,
            0.3342486023902893,
            0.12581685185432434,
            0.12581685185432434,
            0.316038578748703,
            0.36159414052963257,
            0.794084370136261,
            0.794084370136261,
            0.6428364515304565,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
        ],
        "phonemes": [
            {"phoneme": "pau", "frame_length": 2},
            {"phoneme": "t", "frame_length": 8},
            {"phoneme": "e", "frame_length": 2},
            {"phoneme": "s", "frame_length": 1},
            {"phoneme": "u", "frame_length": 1},
            {"phoneme": "t", "frame_length": 2},
            {"phoneme": "o", "frame_length": 1},
            {"phoneme": "pau", "frame_length": 10},
        ],
        "volumeScale": 1.0,
        "outputSamplingRate": 24000,
        "outputStereo": False,
    }
    response = client.post("/frame_synthesis", params={"speaker": style_id}, json=query)

    assert response.status_code == 422
    assert snapshot_json == response.json()


def test_initialize_speaker_with_not_exist_id_422(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    response = client.post(
        "/initialize_speaker", params={"speaker": NOT_EXIST_STYLE_ID}
    )
    assert response.status_code == 422
    assert snapshot_json == response.json()


@pytest.mark.parametrize(
    "style_id", [NOT_EXIST_STYLE_ID, TALK_STYLE_ID, FRAME_DECODE_STYLE_ID]
)
def test_sing_frame_audio_query_with_invalid_style_422(
    client: TestClient, style_id: int, snapshot_json: SnapshotAssertion
) -> None:
    score = {
        "notes": [
            {"id": "a", "key": None, "frame_length": 10, "lyric": ""},
            {"id": "b", "key": 30, "frame_length": 3, "lyric": "て"},
            {"id": "c", "key": 30, "frame_length": 3, "lyric": "す"},
            {"id": "d", "key": 40, "frame_length": 1, "lyric": "と"},
            {"id": "e", "key": None, "frame_length": 10, "lyric": ""},
        ]
    }
    response = client.post(
        "/sing_frame_audio_query", params={"speaker": style_id}, json=score
    )
    assert response.status_code == 422
    assert snapshot_json == response.json()
