from fastapi import FastAPI
from syrupy.extensions.json import JSONSnapshotExtension


def test_OpenAPIの形が変わっていないことを確認(
    app: FastAPI, snapshot_json: JSONSnapshotExtension
) -> None:
    assert snapshot_json == app.openapi()
