from fastapi.testclient import TestClient


def test_fetch_version_success(client: TestClient):
    response = client.get("/version")
    assert response.status_code == 200
    assert isinstance(response.json(), str)
