"""
TTSのテスト
"""

from test.utility import hash_long_string, round_floats

import io
import soundfile as sf
from fastapi.testclient import TestClient
from syrupy.assertion import SnapshotAssertion


def test_テキストと話者IDから音声を合成できる(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    # テキストと話者 ID から AudioQuery を生成する
    audio_query_res = client.post(
        "/audio_query", params={"text": "テストです", "speaker": 0}
    )
    audio_query = audio_query_res.json()

    # AudioQuery から音声波形を生成する
    synthesis_res = client.post("/synthesis", params={"speaker": 0}, json=audio_query)

    # wav ファイルを含む FileResponse から音声波形を抽出する
    wav_bytes = io.BytesIO(synthesis_res.read())
    wave = sf.read(wav_bytes)[0].tolist()

    # NOTE: Linux-Windows 数値精度問題に対するワークアラウンド
    wave = round_floats(wave, 2)

    # リクエストが成功している
    assert synthesis_res.status_code == 200
    # レスポンスが音声ファイルである
    assert synthesis_res.headers['content-type'] == 'audio/wav'
    # 音声波形が commit 間で不変である
    wave_str = " ".join(map(lambda point: str(point), wave))
    assert snapshot_json == hash_long_string(wave_str)
