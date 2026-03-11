"""/frame_synthesis API のテスト。"""

import pytest
from fastapi.testclient import TestClient
from syrupy.assertion import SnapshotAssertion

from test.utility import hash_wave_floats_from_wav_bytes

_query = {
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


def test_post_frame_synthesis_200(
    client: TestClient, snapshot: SnapshotAssertion
) -> None:
    response = client.post("/frame_synthesis", params={"speaker": 4}, json=_query)
    assert response.status_code == 200

    # FileResponse 内の .wav から抽出された音声波形が一致する
    assert response.headers["content-type"] == "audio/wav"
    assert snapshot == hash_wave_floats_from_wav_bytes(response.read())


@pytest.mark.parametrize("style_id", [-1024, 0])
def test_post_frame_synthesis_with_invalid_style_422(
    client: TestClient, style_id: int, snapshot_json: SnapshotAssertion
) -> None:
    response = client.post(
        "/frame_synthesis", params={"speaker": style_id}, json=_query
    )

    assert response.status_code == 422
    assert snapshot_json == response.json()
