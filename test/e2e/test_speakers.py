"""
喋れるキャラクター・歌えるキャラクターのテスト。
TODO: 喋れるキャラクター・歌えるキャラクターの両ドメイン共通のドメイン用語を定め、このテストファイル名を変更する。
"""

from test.utility import hash_long_string

from fastapi.testclient import TestClient
from pydantic import TypeAdapter
from syrupy.assertion import SnapshotAssertion

from voicevox_engine.metas.Metas import Speaker

_speaker_list_adapter = TypeAdapter(list[Speaker])


def test_喋れるキャラクター一覧が取得できる(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    response = client.get("/speakers")
    assert response.status_code == 200
    assert snapshot_json == response.json()


def test_喋れるキャラクターの情報を取得できる(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    speakers = _speaker_list_adapter.validate_python(client.get("/speakers").json())
    for speaker in speakers:
        response = client.get(
            "/speaker_info", params={"speaker_uuid": speaker.speaker_uuid}
        )
        assert snapshot_json(
            name=speaker.speaker_uuid,
        ) == hash_long_string(response.json())


def test_歌えるキャラクター一覧が取得できる(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    response = client.get("/singers")
    assert response.status_code == 200
    assert snapshot_json == response.json()


def test_歌えるキャラクターの情報を取得できる(
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
