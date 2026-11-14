"""/setting API のテスト。"""

import re
from typing import Any

from fastapi.testclient import TestClient
from syrupy.assertion import SnapshotAssertion

from voicevox_engine.app.application import generate_app
from voicevox_engine.setting.model import CorsPolicyMode


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


def test_get_setting_shows_applied_value(app_params: dict[str, Any]) -> None:
    """設定ファイルと異なる値が起動時に適用された場合、適用中の値が設定ページに渡される。"""
    client = TestClient(
        generate_app(
            **app_params,
            cors_policy_mode=CorsPolicyMode.all,
            allow_origin=["http://example.com", "http://example.org"],
        )
    )
    response = client.get("/setting")
    assert response.status_code == 200
    html = response.content.decode("utf-8")
    # フォームの初期値は設定ファイルの値のまま
    assert re.search(r'const corsPolicyMode = ref\(\s*"localapps"', html)
    # 適用中の値は起動時の値
    assert re.search(r'const appliedCorsPolicyMode = ref\(\s*"all"', html)
    assert re.search(
        r'const appliedAllowOrigin = ref\(\s*"http://example.com http://example.org"',
        html,
    )
