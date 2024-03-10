"""
/mora_length API のテスト
"""

from test.e2e.single_api.utils import gen_mora
from test.utility import round_floats

from fastapi.testclient import TestClient
from syrupy.assertion import SnapshotAssertion


def test_post_mora_length_200(
    client: TestClient, snapshot_json: SnapshotAssertion
) -> None:
    accent_phrases = [
        {
            "moras": [
                gen_mora("テ", "t", 2.3, "e", 0.8, 3.3),
                gen_mora("ス", "s", 2.1, "U", 0.3, 0.0),
                gen_mora("ト", "t", 2.3, "o", 1.8, 4.1),
            ],
            "accent": 1,
            "pause_mora": None,
            "is_interrogative": False,
        }
    ]
    response = client.post("/mora_length", params={"speaker": 0}, json=accent_phrases)
    assert response.status_code == 200
    assert snapshot_json == round_floats(response.json(), 2)
