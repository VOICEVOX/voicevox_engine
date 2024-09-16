"""
歌唱のテスト
"""

from test.utility import hash_wave_floats_from_wav_bytes

from fastapi.testclient import TestClient
from syrupy.assertion import SnapshotAssertion


def test_楽譜とキャラクターIDから音声を合成できる(
    client: TestClient, snapshot: SnapshotAssertion
) -> None:
    # 楽譜とキャラクター ID から FrameAudioQuery を生成する
    score = {
        "notes": [
            {"key": None, "frame_length": 10, "lyric": ""},
            {"key": 30, "frame_length": 3, "lyric": "て"},
            {"key": 30, "frame_length": 3, "lyric": "す"},
            {"key": 40, "frame_length": 1, "lyric": "と"},
            {"key": None, "frame_length": 10, "lyric": ""},
        ]
    }
    frame_audio_query_res = client.post(
        "/sing_frame_audio_query", params={"speaker": 0}, json=score
    )
    frame_audio_query = frame_audio_query_res.json()

    # FrameAudioQuery から音声波形を生成する
    frame_synthesis_res = client.post(
        "/frame_synthesis", params={"speaker": 0}, json=frame_audio_query
    )

    # リクエストが成功している
    assert frame_synthesis_res.status_code == 200

    # FileResponse 内の .wav から抽出された音声波形が一致する
    assert frame_synthesis_res.headers["content-type"] == "audio/wav"
    assert snapshot == hash_wave_floats_from_wav_bytes(frame_synthesis_res.read())
