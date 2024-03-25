from typing import Any

from fastapi import FastAPI
from syrupy.assertion import SnapshotAssertion


def test_OpenAPIの形が変わっていないことを確認(
    app: FastAPI, snapshot_json: SnapshotAssertion
) -> None:
    # 変更があった場合はREADMEの「スナップショットの更新」の手順で更新可能
    openapi: Any = (
        app.openapi()
    )  # snapshot_jsonがmypyに対応していないのでワークアラウンド
    assert snapshot_json == openapi
