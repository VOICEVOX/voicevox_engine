"""
話者・歌手のテスト。
TODO: 話者と歌手の両ドメイン共通のドメイン用語を定め、このテストファイル名を変更する。
"""

from test.utility import hash_long_string

from fastapi.testclient import TestClient
from pydantic import parse_obj_as
from syrupy.assertion import SnapshotAssertion

from voicevox_engine.metas.Metas import Speaker


def test_話者一覧が取得できる(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    response = client.get("/speakers")
    assert response.status_code == 200
    assert snapshot_json == response.json()


def test_話者の情報を取得できる(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    speakers = parse_obj_as(list[Speaker], client.get("/speakers").json())
    for speaker in speakers:
        response = client.get(
            "/speaker_info", params={"speaker_uuid": speaker.speaker_uuid}
        )
        assert snapshot_json(
            name=speaker.speaker_uuid,
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
    singers = parse_obj_as(list[Speaker], client.get("/singers").json())
    for singer in singers:
        response = client.get(
            "/singer_info", params={"speaker_uuid": singer.speaker_uuid}
        )
        assert snapshot_json(
            name=singer.speaker_uuid,
        ) == hash_long_string(response.json())
