"""
/import_user_dict APIのテスト
"""

import pytest
from fastapi.testclient import TestClient
from syrupy.assertion import SnapshotAssertion


@pytest.mark.skip(reason="辞書の更新が他のテストに干渉するから")
def test_post_import_user_dict_204(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    user_dict: dict[str, dict[str, str | int]] = {
        "this-is-test-word-1": {
            "accent_associative_rule": "*",
            "accent_type": 1,
            "context_id": 1348,
            "inflectional_form": "*",
            "inflectional_type": "*",
            "mora_count": 3,
            "part_of_speech": "名詞",
            "part_of_speech_detail_1": "固有名詞",
            "part_of_speech_detail_2": "一般",
            "part_of_speech_detail_3": "*",
            "priority": 5,
            "pronunciation": "テストイチ",
            "stem": "*",
            "surface": "ｔｅｓｔ１",
            "yomi": "テストイチ",
        },
    }
    response = client.post("/import_user_dict", json=user_dict)
    assert response.status_code == 204
    assert snapshot_json == response.json()
