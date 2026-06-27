"""`run.py` の環境変数読み込みの単体テスト。"""

import pytest

from run import (
    decide_allow_origin_from_env,
    decide_boolean_from_env_or_none,
    decide_cors_policy_mode_from_env,
)
from voicevox_engine.setting.model import CorsPolicyMode

_ENV_NAME = "VV_TEST_DUMMY"


def test_decide_boolean_from_env_or_none_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """環境変数が存在しない場合は None を返す。"""
    monkeypatch.delenv(_ENV_NAME, raising=False)
    assert decide_boolean_from_env_or_none(_ENV_NAME) is None


def test_decide_boolean_from_env_or_none_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """環境変数が空文字の場合は None を返す。"""
    monkeypatch.setenv(_ENV_NAME, "")
    assert decide_boolean_from_env_or_none(_ENV_NAME) is None


def test_decide_boolean_from_env_or_none_true(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """環境変数が "1" の場合は True を返す。"""
    monkeypatch.setenv(_ENV_NAME, "1")
    assert decide_boolean_from_env_or_none(_ENV_NAME) is True


def test_decide_boolean_from_env_or_none_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """環境変数が "0" の場合は False を返す。"""
    monkeypatch.setenv(_ENV_NAME, "0")
    assert decide_boolean_from_env_or_none(_ENV_NAME) is False


def test_decide_boolean_from_env_or_none_invalid_warns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """認識できない値の場合は警告を出して None を返す。"""
    monkeypatch.setenv(_ENV_NAME, "true")
    with pytest.warns(UserWarning):
        assert decide_boolean_from_env_or_none(_ENV_NAME) is None


def test_decide_cors_policy_mode_from_env_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """環境変数が存在しない場合は None を返す。"""
    monkeypatch.delenv(_ENV_NAME, raising=False)
    assert decide_cors_policy_mode_from_env(_ENV_NAME) is None


def test_decide_cors_policy_mode_from_env_valid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """環境変数が許可モードの場合は対応する値を返す。"""
    monkeypatch.setenv(_ENV_NAME, "all")
    assert decide_cors_policy_mode_from_env(_ENV_NAME) == CorsPolicyMode.all
    monkeypatch.setenv(_ENV_NAME, "localapps")
    assert decide_cors_policy_mode_from_env(_ENV_NAME) == CorsPolicyMode.localapps


def test_decide_cors_policy_mode_from_env_invalid_warns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """認識できない値の場合は警告を出して None を返す。"""
    monkeypatch.setenv(_ENV_NAME, "invalid")
    with pytest.warns(UserWarning):
        assert decide_cors_policy_mode_from_env(_ENV_NAME) is None


def test_decide_allow_origin_from_env_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """環境変数が存在しない場合は None を返す。"""
    monkeypatch.delenv(_ENV_NAME, raising=False)
    assert decide_allow_origin_from_env(_ENV_NAME) is None


def test_decide_allow_origin_from_env_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """環境変数が空文字の場合は None を返す。"""
    monkeypatch.setenv(_ENV_NAME, "")
    assert decide_allow_origin_from_env(_ENV_NAME) is None


def test_decide_allow_origin_from_env_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """環境変数をカンマ区切りでリスト化して返す。"""
    monkeypatch.setenv(_ENV_NAME, "app://.,http://localhost:8080")
    result = decide_allow_origin_from_env(_ENV_NAME)
    assert result == ["app://.", "http://localhost:8080"]


def test_decide_allow_origin_from_env_strips_and_drops_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """各要素の前後の空白を除き、空要素は取り除く。"""
    monkeypatch.setenv(_ENV_NAME, "app://. , http://localhost:8080 ,")
    result = decide_allow_origin_from_env(_ENV_NAME)
    assert result == ["app://.", "http://localhost:8080"]
