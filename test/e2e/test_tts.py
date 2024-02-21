"""
TTSのテスト
"""

from test.utility import hash_long_string

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

    # FileResponse の raw コンテンツを文字列として取得する
    wave = str(synthesis_res.content)

    assert synthesis_res.status_code == 200
    assert snapshot_json == hash_long_string(wave)
