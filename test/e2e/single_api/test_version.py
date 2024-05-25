"""
/version API のテスト
"""

from fastapi.testclient import TestClient

from voicevox_engine import __version__


def test_get_version_200(client: TestClient) -> None:
    response = client.get("/version", params={})
    assert response.status_code == 200
    assert response.json() == __version__
