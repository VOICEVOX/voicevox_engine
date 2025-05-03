"""
ユーザー辞書の言葉のAPIのテスト
"""

import re

from fastapi.testclient import TestClient
from syrupy.assertion import SnapshotAssertion


def test_post_user_dict_word_200(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    params: dict[str, str | int] = {
        "surface": "test",
        "pronunciation": "テスト",
        "accent_type": 1,
        "word_type": "PROPER_NOUN",
        "priority": 5,
    }
    response = client.post("/user_dict_word", params=params)
    assert response.status_code == 200

    # NOTE: ランダム付与される UUID を固定値へ置換する
    response_json = response.json()
    assert isinstance(response_json, str)
    uuidv4_pattern = r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[0-9a-f]{4}-[0-9a-f]{12}"
    response_json = re.sub(uuidv4_pattern, "<uuid_placeholder>", response_json)

    assert snapshot_json == response_json


def test_post_user_dict_word_422(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    params: dict[str, str | int] = {
        "surface": "test",
        "pronunciation": "テスト",
        "accent_type": 1,
        "word_type": "PROPER_NOUN",
        "priority": 100,
    }
    # 範囲外の優先度はエラー
    response = client.post("/user_dict_word", params=params)
    assert response.status_code == 422
    assert snapshot_json == response.json()


def test_put_user_dict_word_204(
    client: TestClient, snapshot: SnapshotAssertion
) -> None:
    word_uuid = "a89596ad-caa8-4f4e-8eb3-3d2261c798fd"
    params: dict[str, str | int] = {
        "surface": "test",
        "pronunciation": "テスト",
        "accent_type": 1,
        "word_uuid": word_uuid,
        "word_type": "PROPER_NOUN",
        "priority": 1,
    }
    response = client.put(f"/user_dict_word/{word_uuid}", params=params)
    assert response.status_code == 204
    assert snapshot == response.content


def test_put_user_dict_word_contents(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    """単語更新は内容が正しく反映されている。"""
    word_uuid = "a89596ad-caa8-4f4e-8eb3-3d2261c798fd"
    params: dict[str, str | int] = {
        "surface": "test",
        "pronunciation": "テスト",
        "accent_type": 1,
        "word_uuid": word_uuid,
        "word_type": "PROPER_NOUN",
        "priority": 1,
    }
    client.put(f"/user_dict_word/{word_uuid}", params=params)
    # NOTE: 'GET /user_dict' が正しく機能することを前提とする
    response = client.get("/user_dict", params={})
    assert snapshot_json == response.json()


def test_put_user_dict_word_422(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    word_uuid = "40400000"
    params: dict[str, str | int] = {
        "surface": "test",
        "pronunciation": "テスト",
        "accent_type": 1,
        "word_uuid": word_uuid,
        "word_type": "PROPER_NOUN",
        "priority": 1,
    }
    # 存在しない word はエラー
    response = client.put(f"/user_dict_word/{word_uuid}", params=params)
    assert response.status_code == 422
    assert snapshot_json == response.json()


def test_delete_user_dict_word_204(
    client: TestClient, snapshot: SnapshotAssertion
) -> None:
    word_uuid = "a89596ad-caa8-4f4e-8eb3-3d2261c798fd"
    response = client.delete(f"/user_dict_word/{word_uuid}", params={})
    assert response.status_code == 204
    assert snapshot == response.content


def test_delete_user_dict_word_contents(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    word_uuid = "a89596ad-caa8-4f4e-8eb3-3d2261c798fd"
    client.delete(f"/user_dict_word/{word_uuid}", params={})
    # NOTE: 'GET /user_dict' が正しく機能することを前提とする
    response = client.get("/user_dict", params={})
    assert snapshot_json == response.json()


def test_delete_user_dict_word_422(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    word_uuid = "40400000"
    # 存在しない word はエラー
    response = client.delete(f"/user_dict_word/{word_uuid}", params={})
    assert response.status_code == 422
    assert snapshot_json == response.json()
