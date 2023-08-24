from generate_test_client import client

def test_fetch_version_success():
    response = client.get("/version")
    assert response.status_code == 200
    assert isinstance(response.json(), str)

