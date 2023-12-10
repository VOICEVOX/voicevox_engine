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


class OjtPhoneme:
    """
    OpenJTalkに含まれる音素
    """

    def __init__(self, phoneme: str):
        # 無音をポーズに変換
        if "sil" in phoneme:
            phoneme = "pau"

        self._phoneme_list = _PHONEME_LIST
        self._num_phoneme = _NUM_PHONEME
        self.phoneme = phoneme

    def __eq__(self, o: object):
        """Deprecated."""
        raise NotImplementedError

    @property
    def phoneme_id(self):
        """
        phoneme_id (phoneme list内でのindex)を取得する
        Returns
        -------
        id : int
            phoneme_idを返す
        """
        return self._phoneme_list.index(self.phoneme)

    @property
    def onehot(self):
        """
        音素onehotベクトル
        Returns
        -------
        onehot : numpy.ndarray
            音素onehotベクトル（listの長さ分の0埋め配列のうち、phoneme id番目が1.0の配列）
        """
        array = numpy.zeros(self._num_phoneme, dtype=numpy.float32)
        array[self.phoneme_id] = 1.0
        return array
