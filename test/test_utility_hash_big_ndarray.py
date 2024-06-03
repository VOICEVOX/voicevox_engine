"""テストユーティリティ `hash_big_ndarray()` のテスト"""

from test.utility import hash_big_ndarray

import numpy as np


def test_hash_big_ndarray_raw_small_array() -> None:
    """`hash_big_ndarray()` は小さい NumPy 配列をハッシュ化しない。"""
    # Inputs
    target = np.array([111.111])
    # Tests
    assert hash_big_ndarray(target) == np.array([111.111])


def test_hash_big_ndarray_raw_big_array() -> None:
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
