"""
/delete_preset API のテスト
"""

import pytest
from fastapi.testclient import TestClient
from syrupy.assertion import SnapshotAssertion


@pytest.mark.skip(reason="プリセット削除が他のテストに干渉するから")
def test_post_delete_preset_204(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    response = client.post("/delete_preset", params={"id": 1})
    assert response.status_code == 204
    assert snapshot_json == response.json()


def test_post_delete_preset_422(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    response = client.post("/delete_preset", params={"id": 4040000000})
    assert response.status_code == 422
    assert snapshot_json == response.json()
