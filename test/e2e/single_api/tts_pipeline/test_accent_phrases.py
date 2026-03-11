"""/accent_phrases API のテスト。"""

import pytest
from fastapi.testclient import TestClient
from syrupy.assertion import SnapshotAssertion

from test.utility import round_floats


def test_post_accent_phrases_200(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    response = client.post(
        "/accent_phrases", params={"text": "テストです", "speaker": 0}
    )
    assert response.status_code == 200
    assert snapshot_json == round_floats(response.json(), 2)


def test_post_accent_phrases_enable_katakana_english_200(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    response = client.post(
        "/accent_phrases",
        params={"text": "Voivo", "speaker": 0, "enable_katakana_english": True},
    )
    assert response.status_code == 200
    assert snapshot_json == round_floats(response.json(), 2)


@pytest.mark.parametrize("style_id", [-1024, 5, 7])
def test_post_accent_phrases_with_invalid_style_422(
    client: TestClient, style_id: int, snapshot_json: SnapshotAssertion
) -> None:
    response = client.post(
        "/accent_phrases", params={"text": "テストです", "speaker": style_id}
    )
    assert response.status_code == 422
    assert snapshot_json == response.json()
