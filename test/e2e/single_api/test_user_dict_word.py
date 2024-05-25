"""
ユーザー辞書の言葉のAPIのテスト
"""

import pytest
from fastapi.testclient import TestClient
from syrupy.assertion import SnapshotAssertion


@pytest.mark.skip(reason="辞書の更新が他のテストに干渉するから")
def test_post_user_dict_word_200(client: TestClient) -> None:
    params: dict[str, str | int] = {
        "surface": "test",
        "pronunciation": "テスト",
        "accent_type": 1,
        "word_type": "PROPER_NOUN",
        "priority": 5,
    }
    response = client.post("/user_dict_word", params=params)
    assert response.status_code == 200


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


@pytest.mark.skip(reason="辞書の更新が他のテストに干渉するから")
def test_put_user_dict_word_204(
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
    response = client.put(f"/user_dict_word/{word_uuid}", params=params)
    assert response.status_code == 204
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


@pytest.mark.skip(reason="辞書の更新が他のテストに干渉するから")
def test_delete_user_dict_word_204(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    word_uuid = "1"
    response = client.delete(f"/user_dict_word/{word_uuid}", params={})
    assert response.status_code == 204
    assert snapshot_json == response.json()


def test_delete_user_dict_word_422(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    word_uuid = "40400000"
    # 存在しない word はエラー
    response = client.delete(f"/user_dict_word/{word_uuid}", params={})
    assert response.status_code == 422
    assert snapshot_json == response.json()
