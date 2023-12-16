"""
APIを無効化するテスト
"""

from typing import Literal

from fastapi.testclient import TestClient

from run import generate_app


# clientとschemaとパスを受け取ってリクエストを送信し、レスポンスが403であることを確認する
def _assert_request_and_response_403(
    client: TestClient,
    method: Literal["post", "get", "put", "delete"],
    path: str,
):
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
    return path


def test_disable_user_dict_api(app_params: dict, opanapi: dict):
    """ユーザー辞書APIを無効化するテスト"""
    client = TestClient(generate_app(**app_params, disable_user_dict_api=True))

    # APIが無効化されているか確認
    checked_paths = {
        _assert_request_and_response_403(client, "get", "/user_dict"),
        _assert_request_and_response_403(client, "post", "/user_dict_word"),
        _assert_request_and_response_403(client, "put", "/user_dict_word/dummy"),
        _assert_request_and_response_403(client, "delete", "/user_dict_word/dummy"),
        _assert_request_and_response_403(client, "post", "/import_user_dict"),
    }

    # APIの数が合っているか確認
    expected_paths = set(path for path in opanapi["paths"] if "user_dict" in path)
    assert len(checked_paths) == len(expected_paths), (
        "実装されているAPIの数と無効化を確認したAPIの数が一致しません\n"
        f"checked_paths: {checked_paths}\n"
        f"expected_paths: {expected_paths}"
    )

    # 他のAPIは有効
    response = client.get("/version")
    assert response.status_code == 200


def test_disable_setting_api(app_params: dict, opanapi: dict):
    """設定APIを無効化するテスト"""
    client = TestClient(generate_app(**app_params, disable_setting_api=True))

    # APIが無効化されている
    checked_paths = {
        _assert_request_and_response_403(client, "post", "/setting"),
        _assert_request_and_response_403(client, "get", "/setting"),
    }

    # APIの数が合っているか確認
    expected_paths = set(path for path in opanapi["paths"] if "setting" in path)
    assert len(checked_paths) == len(expected_paths), (
        "実装されているAPIの数と無効化を確認したAPIの数が一致しません\n"
        f"checked_paths: {checked_paths}\n"
        f"expected_paths: {expected_paths}"
    )

    # 他のAPIは有効
    response = client.get("/version")
    assert response.status_code == 200
