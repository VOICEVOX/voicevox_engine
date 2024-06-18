"""
話者・歌手のテスト。
TODO: 話者と歌手の両ドメイン共通のドメイン用語を定め、このテストファイル名を変更する。
"""

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


def test_話者一覧が取得できる(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    response = client.get("/speakers")
    assert response.status_code == 200
    assert snapshot_json == response.json()


def test_話者の情報を取得できる(
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


def test_話者の情報をURLで取得できる(
    client: TestClient, snapshot_json: SnapshotAssertion, snapshot: SnapshotAssertion
) -> None:
    speakers = _speaker_list_adapter.validate_json(client.get("/speakers").content)
    for speaker in speakers:
        speaker_id = speaker.speaker_uuid
        response = client.get(
            "/speaker_info",
            params={"speaker_uuid": speaker_id, "resource_format": "url"},
        )
        assert snapshot_json(name=speaker_id) == response.json()

        speaker_info = SpeakerInfo.model_validate_json(response.content)
        _assert_resource_url(
            client, snapshot, speaker_info.portrait, f"{speaker_id}_portrait"
        )

        for style in speaker_info.style_infos:
            _assert_resource_url(
                client, snapshot, style.icon, f"{speaker_id}_{style.id}_icon"
            )
            if style.portrait is not None:
                _assert_resource_url(
                    client,
                    snapshot,
                    style.portrait,
                    f"{speaker_id}_{style.id}_portrait",
                )
            for i, voice_sample in enumerate(style.voice_samples):
                _assert_resource_url(
                    client,
                    snapshot,
                    voice_sample,
                    f"{speaker_id}_{style.id}_voice_sample_{i}",
                )


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


def test_歌手の情報をURLで取得できる(
    client: TestClient, snapshot_json: SnapshotAssertion, snapshot: SnapshotAssertion
) -> None:
    singers = _speaker_list_adapter.validate_json(client.get("/singers").content)
    for singer in singers:
        singer_id = singer.speaker_uuid
        response = client.get(
            "/singer_info",
            params={"speaker_uuid": singer_id, "resource_format": "url"},
        )
        assert snapshot_json(name=singer_id) == response.json()

        speaker_info = SpeakerInfo.model_validate_json(response.content)
        _assert_resource_url(
            client, snapshot, speaker_info.portrait, f"{singer_id}_portrait"
        )

        for style in speaker_info.style_infos:
            _assert_resource_url(
                client, snapshot, style.icon, f"{singer_id}_{style.id}_icon"
            )
            if style.portrait is not None:
                _assert_resource_url(
                    client, snapshot, style.portrait, f"{singer_id}_{style.id}_portrait"
                )
            for i, voice_sample in enumerate(style.voice_samples):
                _assert_resource_url(
                    client,
                    snapshot,
                    voice_sample,
                    f"{singer_id}_{style.id}_voice_sample_{i}",
                )
