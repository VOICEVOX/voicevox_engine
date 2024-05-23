"""
/sing_frame_audio_query API のテスト
"""

from test.utility import round_floats

from fastapi.testclient import TestClient
from syrupy.assertion import SnapshotAssertion


def test_post_sing_frame_audio_query_200(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    score = {
        "notes": [
            {"key": None, "frame_length": 10, "lyric": ""},
            {"key": 30, "frame_length": 3, "lyric": "て"},
            {"key": 30, "frame_length": 3, "lyric": "す"},
            {"key": 40, "frame_length": 1, "lyric": "と"},
            {"key": None, "frame_length": 10, "lyric": ""},
        ]
    }
    response = client.post("/sing_frame_audio_query", params={"speaker": 0}, json=score)
    assert response.status_code == 200
    assert snapshot_json == round_floats(response.json(), 2)
