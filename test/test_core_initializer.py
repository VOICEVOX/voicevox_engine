from unittest.mock import patch

from voicevox_engine.core.core_initializer import get_half_logical_cores


@patch("os.cpu_count", return_value=8)
def test_half_logical_cores_even(mock_cpu_count: int) -> None:
    assert get_half_logical_cores() == 4


@patch("os.cpu_count", return_value=9)
def test_half_logical_cores_odd(mock_cpu_count: int) -> None:
    assert get_half_logical_cores() == 4


@patch("os.cpu_count", return_value=None)
def test_half_logical_cores_none(mock_cpu_count: int) -> None:
    assert get_half_logical_cores() == 0
