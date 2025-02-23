"""
/validate_kana API のテスト
"""

from fastapi.testclient import TestClient
from syrupy.assertion import SnapshotAssertion


def test_post_validate_kana_200(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    response = client.post("/validate_kana", params={"text": "コンニチワ'"})
    assert response.status_code == 200
    assert snapshot_json == response.json()


def test_post_validate_kana_400(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    # textがAquesTalk 風記法に従っていないため、400エラーになる
    response = client.post("/validate_kana", params={"text": "こんにちは"})
    assert response.status_code == 400
    assert snapshot_json == response.json()


def test_post_validate_kana_422(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    # queryパラメータにtextが無いため、422エラーになる
    response = client.post("/validate_kana")
    assert response.status_code == 422
    assert snapshot_json == response.json()
