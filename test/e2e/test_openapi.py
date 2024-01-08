from fastapi import FastAPI
from syrupy.extensions.json import JSONSnapshotExtension


def test_OpenAPIの形が変わっていないことを確認(
    app: FastAPI, snapshot_json: JSONSnapshotExtension
) -> None:
    # 変更があった場合はREADMEの「スナップショットの更新」の手順で更新可能
    assert snapshot_json == app.openapi()
