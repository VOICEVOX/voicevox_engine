"""
/import_user_dict APIのテスト
"""

from fastapi.testclient import TestClient
from syrupy.assertion import SnapshotAssertion


def test_post_import_user_dict_204(
    client: TestClient, snapshot: SnapshotAssertion
) -> None:
    user_dict: dict[str, dict[str, str | int]] = {}
    response = client.post(
        "/import_user_dict", json=user_dict, params={"override": True}
    )
    assert response.status_code == 204
    assert snapshot == response.content


def test_post_import_user_dict_contents(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    """辞書インポートは内容が正しく反映されている。"""

    user_dict: dict[str, dict[str, str | int]] = {
        "a11196ad-caa8-4f4e-8eb3-3d2261c798fd": {
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
            "priority": 4,
            "pronunciation": "テストサン",
            "stem": "*",
            "surface": "ｔｅｓｔ３",
            "yomi": "テストサン",
        },
    }
    client.post("/import_user_dict", json=user_dict, params={"override": True})
    # NOTE: 'GET /user_dict' が正しく機能することを前提とする
    response = client.get("/user_dict", params={})
    assert snapshot_json == response.json()
