"""音素"""

from typing import Literal

import numpy as np
from numpy.typing import NDArray

# NOTE: `Vowel` は母音 (a/i/u/e/o の有声・無声) + 無音 pau + 撥音 N ("ん") + 促音 cl ("っ")
# NOTE: 型の名称は暫定的
BaseVowel = Literal["pau", "N", "a", "cl", "e", "i", "o", "u"]
Vowel = BaseVowel | Literal["A", "E", "I", "O", "U"]

Consonant = Literal[
    "b",
    "by",
    "ch",
    "d",
    "dy",
    "f",
    "g",
    "gw",
    "gy",
    "h",
    "hy",
    "j",
    "k",
    "kw",
    "ky",
    "m",
    "my",
    "n",
    "ny",
    "p",
    "py",
    "r",
    "ry",
    "s",
    "sh",
    "t",
    "ts",
    "ty",
    "v",
    "w",
    "y",
    "z",
]

# 音素のリスト
_PHONEME_LIST: tuple[Vowel | Consonant, ...] = ()
_PHONEME_LIST += ("pau", "A", "E", "I", "N", "O", "U", "a", "b", "by")
_PHONEME_LIST += ("ch", "cl", "d", "dy", "e", "f", "g", "gw", "gy", "h")
_PHONEME_LIST += ("hy", "i", "j", "k", "kw", "ky", "m", "my", "n", "ny")
_PHONEME_LIST += ("o", "p", "py", "r", "ry", "s", "sh", "t", "ts", "ty")
_PHONEME_LIST += ("u", "v", "w", "y", "z")

# 音素リストの要素数
_NUM_PHONEME = len(_PHONEME_LIST)

_UNVOICED_MORA_TAIL_PHONEMES = ["A", "I", "U", "E", "O", "cl", "pau"]
_MORA_TAIL_PHONEMES = ["a", "i", "u", "e", "o", "N"] + _UNVOICED_MORA_TAIL_PHONEMES


class Phoneme:
    """音素"""

    _PHONEME_LIST = _PHONEME_LIST
    _NUM_PHONEME = _NUM_PHONEME

    def __init__(self, phoneme: str):
        # 無音をポーズに変換
        if "sil" in phoneme:
            phoneme = "pau"

        self._phoneme = phoneme
        # TODO: `phoneme` で受け入れ可能な文字列を型で保証
        # self.phoneme: Vowel | Consonant = phoneme

    @property
    def id(self) -> int:
        """音素ID (音素リスト内でのindex) を取得する"""
        return self._PHONEME_LIST.index(self._phoneme)

    @property
    def onehot(self) -> NDArray[np.float32]:
        """音素onehotベクトルを取得する"""
        vec = np.zeros(self._NUM_PHONEME, dtype=np.float32)
        vec[self.id] = 1.0
        return vec

    def is_mora_tail(self) -> bool:
        """この音素はモーラ末尾音素（母音・撥音・促音・無音）である"""
        return self._phoneme in _MORA_TAIL_PHONEMES

    def is_unvoiced_mora_tail(self) -> bool:
        """この音素は無声のモーラ末尾音素（無声母音・促音・無音）である"""
        return self._phoneme in _UNVOICED_MORA_TAIL_PHONEMES
