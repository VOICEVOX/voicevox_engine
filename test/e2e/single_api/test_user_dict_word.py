"""
ユーザー辞書の言葉のAPIのテスト
"""

from fastapi.testclient import TestClient
from syrupy.assertion import SnapshotAssertion


def test_post_user_dict_word(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    true_params: dict[str, str | int] = {
        "surface": "test",
        "pronunciation": "テスト",
        "accent_type": 1,
        "word_type": "PROPER_NOUN",
        "priority": 5,
    }

    # 正常系
    response = client.post("/user_dict_word", params=true_params)
    assert response.status_code == 200

    # 範囲外の優先度はエラー
    response = client.post("/user_dict_word", params={**true_params, "priority": 100})
    assert response.status_code == 422
    assert snapshot_json == response.json()
