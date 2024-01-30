"""
話者・歌手のテスト。
TODO: 話者と歌手の両ドメイン共通のドメイン用語を定め、このテストファイル名を変更する。
"""

from fastapi.testclient import TestClient
from pydantic import parse_obj_as
from syrupy import filters
from syrupy.extensions.json import JSONSnapshotExtension

from voicevox_engine.metas.Metas import Speaker


def test_話者一覧が取得できる(client: TestClient, snapshot_json: JSONSnapshotExtension) -> None:
    response = client.get("/speakers")
    assert response.status_code == 200
    assert snapshot_json == response.json()


def test_話者の情報を取得できる(client: TestClient, snapshot_json: JSONSnapshotExtension) -> None:
    speakers = parse_obj_as(list[Speaker], client.get("/speakers").json())
    for speaker in speakers:
        speaker_info_json = client.get(
            "/speaker_info", params={"speaker_uuid": speaker.speaker_uuid}
        ).json()
        assert (
            snapshot_json(
                name=speaker.speaker_uuid,
                exclude=filters.props(
                    "portrait", "icon", "voice_samples"
                ),  # バイナリファイル系は除外
            )
            == speaker_info_json
        )
