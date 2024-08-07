"""
APIを無効化するテスト
"""

from typing import Literal

from fastapi.testclient import TestClient

from voicevox_engine.app.application import generate_app


# clientとschemaとパスを受け取ってリクエストを送信し、レスポンスが403であることを確認する
def _assert_request_and_response_403(
    client: TestClient,
    method: Literal["post", "get", "put", "delete"],
    path: str,
) -> None:
    if method == "post":
        response = client.post(path)
    elif method == "get":
        response = client.get(path)
    elif method == "put":
        response = client.put(path)
    elif method == "delete":
        response = client.delete(path)
    else:
        raise ValueError("methodはpost, get, put, deleteのいずれかである必要があります")

    assert response.status_code == 403, f"{method} {path} が403を返しませんでした"


def test_disable_mutable_api(app_params: dict) -> None:
    """エンジンの静的なデータを変更するAPIを無効化するテスト"""
    client = TestClient(generate_app(**app_params, disable_mutable_api=True))

    # APIが無効化されているか確認
    _assert_request_and_response_403(client, "post", "/add_preset")
    _assert_request_and_response_403(client, "post", "/update_preset")
    _assert_request_and_response_403(client, "post", "/delete_preset")
    _assert_request_and_response_403(client, "post", "/user_dict_word")
    _assert_request_and_response_403(client, "put", "/user_dict_word/dummy")
    _assert_request_and_response_403(client, "delete", "/user_dict_word/dummy")
    _assert_request_and_response_403(client, "post", "/import_user_dict")
    _assert_request_and_response_403(client, "post", "/setting")

    # FIXME: EngineManifestをDI可能にし、EngineManifestに従ってこれらのAPIを加える
    # _assert_request_and_response_403(client, "post", "/install_library/dummy")
    # _assert_request_and_response_403(client, "post", "/uninstall_library/dummy")

    # 他のAPIは有効
    response = client.get("/version")
    assert response.status_code == 200
