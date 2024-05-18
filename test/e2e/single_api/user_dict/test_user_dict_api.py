"""
/user_dict API のテスト
"""

import pytest
from fastapi.testclient import TestClient
from syrupy.assertion import SnapshotAssertion


@pytest.mark.skip(reason="他テストによる辞書の更新で干渉されうるから")
def test_get_user_dict_200(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    response = client.get("/user_dict", params={})
    assert response.status_code == 200
    assert snapshot_json == response.json()
