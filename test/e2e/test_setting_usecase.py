"""設定変更のテスト。"""

import re

from fastapi.testclient import TestClient


def test_設定を変更すると設定ページに反映される(client: TestClient) -> None:
    allow_origin = "http://example.com"

    # 設定を変更する
    post_res = client.post(
        "/setting", data={"cors_policy_mode": "all", "allow_origin": allow_origin}
    )
    assert post_res.status_code == 204

    # 変更した設定が設定ページに反映される
    get_res = client.get("/setting")
    assert get_res.status_code == 200
    assert re.search(r'corsPolicyMode = ref\(\s*"all",?\s*\)', get_res.text)
    assert allow_origin in get_res.text
