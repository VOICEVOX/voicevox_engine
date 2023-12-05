import numpy


class OjtPhoneme:
    """
    OpenJTalkに含まれる音素群クラス

    Attributes
    ----------
    phoneme_list : Sequence[str]
        音素のリスト
    num_phoneme : int
        音素リストの要素数
    space_phoneme : str
        読点に値する音素
    """

    phoneme_list = (
        "pau",
        "A",
        "E",
        "I",
        "N",
        "O",
        "U",
        "a",
        "b",
        "by",
        "ch",
        "cl",
        "d",
        "dy",
        "e",
        "f",
        "g",
        "gw",
        "gy",
        "h",
        "hy",
        "i",
        "j",
        "k",
        "kw",
        "ky",
        "m",
        "my",
        "n",
        "ny",
        "o",
        "p",
        "py",
        "r",
        "ry",
        "s",
        "sh",
        "t",
        "ts",
        "ty",
        "u",
        "v",
        "w",
        "y",
        "z",
    )
    num_phoneme = len(phoneme_list)
    space_phoneme = "pau"

    def __init__(
        self,
        phoneme: str,
        start: float,
        end: float,
    ):
        # `sil`-to-`pau` (silent to space_phoneme) conversion
        if "sil" in phoneme:
            phoneme = self.space_phoneme

        self.phoneme = phoneme
        self.start = numpy.round(start, decimals=2)
        self.end = numpy.round(end, decimals=2)

    def __repr__(self):
        return f"Phoneme(phoneme='{self.phoneme}', start={self.start}, end={self.end})"

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
        return self.phoneme_list.index(self.phoneme)

    @property
    def onehot(self):
        """
        音素onehotベクトル
        Returns
        -------
        onehot : numpy.ndarray
            音素onehotベクトル（listの長さ分の0埋め配列のうち、phoneme id番目が1.0の配列）
        """
        array = numpy.zeros(self.num_phoneme, dtype=numpy.float32)
        array[self.phoneme_id] = 1.0
        return array
