from generate_test_client import client
from voicevox_engine import __version__

def test_fetch_version_success():
    response = client.get("/version")
    assert response.status_code == 200
    assert response.json() == __version__
