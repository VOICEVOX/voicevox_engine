"""/setting API のテスト。"""

import json
import re

import pytest
from fastapi.testclient import TestClient
from syrupy.assertion import SnapshotAssertion


def test_get_setting_200(client: TestClient, snapshot: SnapshotAssertion) -> None:
    response = client.get("/setting")
    assert response.status_code == 200
    # HTML string をテスト
    assert snapshot == response.content.decode("utf-8")


def test_post_setting_204(client: TestClient, snapshot: SnapshotAssertion) -> None:
    response = client.post(
        "/setting", data={"cors_policy_mode": "all", "allow_origin": "vv"}
    )
    assert response.status_code == 204
    assert snapshot == response.content


@pytest.mark.parametrize(
    "allow_origin",
    [
        "https://example.com",
        'https://example.com/"quoted"',
        "line\\backslash\nnext_line",
        "</script><p>test marker</p>",
        "日本語と特殊文字 <>&'\"",
    ],
)
def test_get_setting_escapes_allow_origin(
    client: TestClient, allow_origin: str
) -> None:
    response = client.post(
        "/setting",
        data={"cors_policy_mode": "localapps", "allow_origin": allow_origin},
    )
    assert response.status_code == 204

    response = client.get("/setting")
    assert response.status_code == 200

    match = re.search(r"const allowOrigin = ref\((.*?)\);", response.text)
    assert match is not None
    assert json.loads(match.group(1)) == allow_origin
    assert "<" not in match.group(1)
