"""テストユーティリティ `summarize_big_ndarray()` のテスト"""

from test.utility import summarize_big_ndarray

import numpy as np


def test_summarize_big_ndarray_raw_small_array() -> None:
    """`summarize_big_ndarray()` は小さい NumPy 配列を要約しない。"""
    # Inputs
    target = np.array([111.111])
    # Tests
    assert summarize_big_ndarray(target) == np.array([111.111])


def test_summarize_big_ndarray_raw_big_array() -> None:
    """`summarize_big_ndarray()` は大きい NumPy 配列を要約する。"""
    # Inputs
    target = np.ones([10, 10, 10])
    # Expects
    true_hash_header = "MD5:"
    true_shape = target.shape
    # Outputs
    summary = summarize_big_ndarray(target)
    hash_header = summary["hash"][:4]
    shape = tuple(summary["shape"])
    # Tests
    assert true_hash_header == hash_header
    assert true_shape == shape
