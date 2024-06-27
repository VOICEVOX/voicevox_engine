"""キャラクターのテスト"""

import hashlib
from test.utility import hash_long_string

from fastapi.testclient import TestClient
from pydantic import TypeAdapter
from syrupy.assertion import SnapshotAssertion

from voicevox_engine.metas.Metas import Speaker, SpeakerInfo

_speaker_list_adapter = TypeAdapter(list[Speaker])


def _hash_bytes(value: bytes) -> str:
    """バイト列をハッシュ化する"""
    return "MD5:" + hashlib.md5(value).hexdigest()


def _assert_resource_url(
    client: TestClient, snapshot: SnapshotAssertion, url: str, name: str
) -> None:
    """
    URLからデータが正しく取得できるかスナップショットテストをする
    """
    response = client.get(url)
    assert response.status_code == 200
    assert snapshot(name=name) == _hash_bytes(response.content)


def test_喋れるキャラクター一覧が取得できる(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    response = client.get("/speakers")
    assert response.status_code == 200
    assert snapshot_json == response.json()


def test_喋れるキャラクターの情報を取得できる(
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


def test_喋れるキャラクターの情報をURLで取得できる(
    client: TestClient, snapshot_json: SnapshotAssertion, snapshot: SnapshotAssertion
) -> None:
    def assert_resource_url(url: str, name: str) -> None:
        _assert_resource_url(client, snapshot, url, name)

    speakers = _speaker_list_adapter.validate_json(client.get("/speakers").content)
    for speaker in speakers:
        speaker_id = speaker.speaker_uuid
        response = client.get(
            "/speaker_info",
            params={"speaker_uuid": speaker_id, "resource_format": "url"},
        )
        assert snapshot_json(name=speaker_id) == response.json()

        speaker_info = SpeakerInfo.model_validate_json(response.content)
        assert_resource_url(speaker_info.portrait, f"{speaker_id}_portrait")

        for style in speaker_info.style_infos:
            assert_resource_url(style.icon, f"{speaker_id}_{style.id}_icon")
            if style.portrait is not None:
                assert_resource_url(style.portrait, f"{speaker_id}_{style.id}_portrait")
            for i, voice_sample in enumerate(style.voice_samples):
                assert_resource_url(
                    voice_sample, f"{speaker_id}_{style.id}_voice_sample_{i}"
                )


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


def test_歌えるキャラクターの情報をURLで取得できる(
    client: TestClient, snapshot_json: SnapshotAssertion, snapshot: SnapshotAssertion
) -> None:
    def assert_resource_url(url: str, name: str) -> None:
        _assert_resource_url(client, snapshot, url, name)

    singers = _speaker_list_adapter.validate_json(client.get("/singers").content)
    for singer in singers:
        singer_id = singer.speaker_uuid
        response = client.get(
            "/singer_info",
            params={"speaker_uuid": singer_id, "resource_format": "url"},
        )
        assert snapshot_json(name=singer_id) == response.json()

        speaker_info = SpeakerInfo.model_validate_json(response.content)
        assert_resource_url(speaker_info.portrait, f"{singer_id}_portrait")

        for style in speaker_info.style_infos:
            assert_resource_url(style.icon, f"{singer_id}_{style.id}_icon")
            if style.portrait is not None:
                assert_resource_url(style.portrait, f"{singer_id}_{style.id}_portrait")
            for i, voice_sample in enumerate(style.voice_samples):
                assert_resource_url(
                    voice_sample, f"{singer_id}_{style.id}_voice_sample_{i}"
                )
