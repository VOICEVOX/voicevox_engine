"""/is_initialized_speaker API のテスト。"""

from fastapi.testclient import TestClient
from syrupy.assertion import SnapshotAssertion

from test.utility import NOT_EXIST_STYLE_ID


def test_get_is_initialized_speaker_200(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    response = client.get("/is_initialized_speaker", params={"speaker": 0})
    assert response.status_code == 200
    assert snapshot_json == response.json()


def test_get_is_initialized_speaker_with_not_exist_id_422(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    response = client.get(
        "/is_initialized_speaker", params={"speaker": NOT_EXIST_STYLE_ID}
    )
    assert response.status_code == 422
    assert snapshot_json == response.json()
