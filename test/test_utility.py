"""テストユーティリティのテスト"""

from test.utility import hash_big_ndarray, round_floats

import numpy as np

# round_floats()


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


# hash_big_ndarray()


def test_hash_big_ndarray_raw_small_array() -> None:
    """`hash_big_ndarray()` は小さい NumPy 配列をハッシュ化しない。"""
    # Inputs
    target = np.array([111.111])
    # Tests
    assert hash_big_ndarray(target) == np.array([111.111])


def test_hash_big_ndarray_raw_small_array() -> None:
    """`hash_big_ndarray()` は大きい NumPy 配列をハッシュ化する。"""
    # Inputs
    target = np.ones([10, 10, 10])
    # Expects
    true_hashed_header = "MD5:"
    # Outputs
    hashed = hash_big_ndarray(target)
    hashed_header = hashed[:4]
    # Tests
    assert true_hashed_header == hashed_header
