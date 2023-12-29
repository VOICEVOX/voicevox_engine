import numpy

# 音素のリスト
_P_LIST1 = ("pau", "A", "E", "I", "N", "O", "U", "a", "b", "by")
_P_LIST2 = ("ch", "cl", "d", "dy", "e", "f", "g", "gw", "gy", "h")
_P_LIST3 = ("hy", "i", "j", "k", "kw", "ky", "m", "my", "n", "ny")
_P_LIST4 = ("o", "p", "py", "r", "ry", "s", "sh", "t", "ts", "ty")
_P_LIST5 = ("u", "v", "w", "y", "z")
_PHONEME_LIST = _P_LIST1 + _P_LIST2 + _P_LIST3 + _P_LIST4 + _P_LIST5

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

    def __eq__(self, o: object):  # type:ignore[no-untyped-def]
        """Deprecated."""
        raise NotImplementedError

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
