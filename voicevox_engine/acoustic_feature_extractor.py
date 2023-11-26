from abc import abstractmethod
from typing import List, Sequence

import numpy


class BasePhoneme(object):
    """
    音素の応用クラス群の抽象基底クラス

    Attributes
    ----------
    phoneme_list : Sequence[str]
        音素のリスト
    num_phoneme : int
        音素リストの要素数
    space_phoneme : str
        読点に値する音素
    """

    phoneme_list: Sequence[str]
    num_phoneme: int
    space_phoneme: str

    def __init__(
        self,
        phoneme: str,
        start: float,
        end: float,
    ):
        self.phoneme = phoneme
        self.start = numpy.round(start, decimals=2)
        self.end = numpy.round(end, decimals=2)

    def __repr__(self):
        return f"Phoneme(phoneme='{self.phoneme}', start={self.start}, end={self.end})"

    def __eq__(self, o: object):
        return isinstance(o, BasePhoneme) and (
            self.phoneme == o.phoneme and self.start == o.start and self.end == o.end
        )

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
        phoneme listの長さ分の0埋め配列のうち、phoneme id番目がTrue(1)の配列を返す
        Returns
        -------
        onehot : numpu.ndarray
            関数内で変更された配列を返す
        """
        array = numpy.zeros(self.num_phoneme, dtype=bool)
        array[self.phoneme_id] = True
        return array

    @classmethod
    @abstractmethod
    def convert(cls, phonemes: List["BasePhoneme"]) -> List["BasePhoneme"]:
        raise NotImplementedError


class OjtPhoneme(BasePhoneme):
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

    @classmethod
    def convert(cls, phonemes: List["OjtPhoneme"]):
        """
        最初と最後のsil(silent)をspace_phoneme(pau)に置き換え(変換)する
        Parameters
        ----------
        phonemes : List[OjtPhoneme]
            変換したいphonemeのリスト

        Returns
        -------
        phonemes : List[OjtPhoneme]
            変換されたphonemeのリスト
        """
        if "sil" in phonemes[0].phoneme:
            phonemes[0].phoneme = cls.space_phoneme
        if "sil" in phonemes[-1].phoneme:
            phonemes[-1].phoneme = cls.space_phoneme
        return phonemes
