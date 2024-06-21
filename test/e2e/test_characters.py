"""話者・歌手のテスト"""

from test.utility import hash_long_string

from fastapi.testclient import TestClient
from pydantic import TypeAdapter
from syrupy.assertion import SnapshotAssertion

from voicevox_engine.metas.Metas import Speaker

_speaker_list_adapter = TypeAdapter(list[Speaker])


def test_話者一覧が取得できる(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    response = client.get("/speakers")
    assert response.status_code == 200
    assert snapshot_json == response.json()


def test_話者の情報を取得できる(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    talkers = _speaker_list_adapter.validate_python(client.get("/speakers").json())
    for talker in talkers:
        response = client.get(
            "/speaker_info", params={"speaker_uuid": talker.speaker_uuid}
        )
        assert snapshot_json(
            name=talker.speaker_uuid,
        ) == hash_long_string(response.json())


def test_歌手一覧が取得できる(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    response = client.get("/singers")
    assert response.status_code == 200
    assert snapshot_json == response.json()


def test_歌手の情報を取得できる(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    singers = _speaker_list_adapter.validate_python(client.get("/singers").json())
    for singer in singers:
        response = client.get(
            "/singer_info", params={"speaker_uuid": singer.speaker_uuid}
        )
        assert snapshot_json(
            name=singer.speaker_uuid,
        ) == hash_long_string(response.json())
