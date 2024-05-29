"""テストユーティリティのテスト"""

import numpy as np
from test.utility import round_floats


def test_round_floats_raw_float() -> None:
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