from typing import Literal

import numpy

# NOTE: `Vowel` は母音 (a/i/u/e/o の有声・無声) + 無音 pau + 撥音 N ("ん") + 促音 cl ("っ")
Vowel = Literal["pau", "A", "E", "I", "N", "O", "U", "a", "cl", "e", "i", "o", "u"]
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
_P_LIST1 = ("pau", "A", "E", "I", "N", "O", "U", "a", "b", "by")
_P_LIST2 = ("ch", "cl", "d", "dy", "e", "f", "g", "gw", "gy", "h")
_P_LIST3 = ("hy", "i", "j", "k", "kw", "ky", "m", "my", "n", "ny")
_P_LIST4 = ("o", "p", "py", "r", "ry", "s", "sh", "t", "ts", "ty")
_P_LIST5 = ("u", "v", "w", "y", "z")
_PHONEME_LIST: tuple[Vowel | Consonant] = (
    _P_LIST1 + _P_LIST2 + _P_LIST3 + _P_LIST4 + _P_LIST5
)

# 音素リストの要素数
_NUM_PHONEME = len(_PHONEME_LIST)


class Phoneme:
    """音素"""

    _PHONEME_LIST = _PHONEME_LIST
    _NUM_PHONEME = _NUM_PHONEME

    def __init__(self, phoneme: str):
        # 無音をポーズに変換
        if "sil" in phoneme:
            phoneme = "pau"

        self.phoneme = phoneme
        # TODO: `phoneme` で受け入れ可能な文字列を型で保証
        # self.phoneme: Vowel | Consonant = phoneme

    @property
    def phoneme_id(self) -> int:
        """音素ID (音素リスト内でのindex) を取得する"""
        return self._PHONEME_LIST.index(self.phoneme)

    @property
    def onehot(self):
        """音素onehotベクトルを取得する"""
        vec = numpy.zeros(self._NUM_PHONEME, dtype=numpy.float32)
        vec[self.phoneme_id] = 1.0
        return vec
