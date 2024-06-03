"""テストユーティリティ `round_floats()` のテスト"""

from test.utility import round_floats

import numpy as np


def test_round_floats_raw_float() -> None:
    """`round_floats()` は値を丸める。"""
    # Inputs
    target = 111.111
    # Tests
    assert round_floats(target, -2) == 100
    assert round_floats(target, -1) == 110
    assert round_floats(target, 0) == 111
    assert round_floats(target, +1) == 111.1
    assert round_floats(target, +2) == 111.11


def test_round_floats_list() -> None:
    """`round_floats()` はリスト内の値を丸める。"""
    # Inputs
    target = [1.111, 8.888]
    # Tests
    assert round_floats(target, 2) == [1.11, 8.89]


def test_round_floats_dict() -> None:
    """`round_floats()` は辞書内の値を丸める。"""
    # Inputs
    target = {"hello": 1.111}
    # Tests
    assert round_floats(target, 2) == {"hello": 1.11}


def test_round_floats_numpy() -> None:
    """`round_floats()` は NumPy 値を丸める。"""
    # Inputs
    target = np.array([111.111])
    # Tests
    assert round_floats(target, 2) == np.array([111.11])


def test_round_floats_nested() -> None:
    """`round_floats()` はネストしたオブジェクト内の値を丸める。"""
    # Inputs
    target = [1.111, {"hello": 1.111, "world": [1.111]}, np.array([1.111])]
    # Expects
    true_rounded = [1.11, {"hello": 1.11, "world": [1.11]}, np.array([1.11])]
    # Outputs
    rounded = round_floats(target, 2)
    # Tests
    assert true_rounded == rounded
