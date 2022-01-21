from abc import abstractmethod
from enum import Enum
from pathlib import Path
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

    def verify(self):
        """
        音素クラスとして、データが正しいかassertする
        """
        assert self.phoneme in self.phoneme_list, f"{self.phoneme} is not defined."

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
    def duration(self):
        """
        音素継続期間を取得する
        Returns
        -------
        duration : int
            音素継続期間を返す
        """
        return self.end - self.start

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
    def parse(cls, s: str):
        """
        文字列をパースして音素クラスを作る
        Parameters
        ----------
        s : str
            パースしたい文字列

        Returns
        -------
        phoneme : BasePhoneme
            パース結果を用いた音素クラスを返す

        Examples
        --------
        >>> BasePhoneme.parse('1.7425000 1.9125000 o:')
        Phoneme(phoneme='o:', start=1.74, end=1.91)
        """
        words = s.split()
        return cls(
            start=float(words[0]),
            end=float(words[1]),
            phoneme=words[2],
        )

    @classmethod
    @abstractmethod
    def convert(cls, phonemes: List["BasePhoneme"]) -> List["BasePhoneme"]:
        raise NotImplementedError

    @classmethod
    def load_lab_list(cls, path: Path):
        """
        labファイルを読み込む
        Parameters
        ----------
        path : Path
            読み込みたいlabファイルのパス

        Returns
        -------
        phonemes : List[BasePhoneme]
            パース結果を用いた音素クラスを返す
        """
        phonemes = [cls.parse(s) for s in path.read_text().split("\n") if len(s) > 0]
        phonemes = cls.convert(phonemes)

        for phoneme in phonemes:
            phoneme.verify()
        return phonemes

    @classmethod
    def save_lab_list(cls, phonemes: List["BasePhoneme"], path: Path):
        """
        音素クラスのリストをlabファイル形式で保存する
        Parameters
        ----------
        phonemes : List[BasePhoneme]
            保存したい音素クラスのリスト
        path : Path
            labファイルの保存先パス
        """
        text = "\n".join(
            [
                f"{numpy.round(p.start, decimals=2):.2f}\t"
                f"{numpy.round(p.end, decimals=2):.2f}\t"
                f"{p.phoneme}"
                for p in phonemes
            ]
        )
        path.write_text(text)


class JvsPhoneme(BasePhoneme):
    """
    JVS(Japanese versatile speech)コーパスに含まれる音素群クラス

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
        "I",
        "N",
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
        "gy",
        "h",
        "hy",
        "i",
        "j",
        "k",
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
        "u",
        "v",
        "w",
        "y",
        "z",
    )
    num_phoneme = len(phoneme_list)
    space_phoneme = "pau"

    @classmethod
    def convert(cls, phonemes: List["JvsPhoneme"]) -> List["JvsPhoneme"]:
        """
        最初と最後のsil(silent)をspace_phoneme(pau)に置き換え(変換)する
        Parameters
        ----------
        phonemes : List[JvsPhoneme]
            変換したいphonemeのリスト

        Returns
        -------
        phonemes : List[JvsPhoneme]
            変換されたphonemeのリスト
        """
        if "sil" in phonemes[0].phoneme:
            phonemes[0].phoneme = cls.space_phoneme
        if "sil" in phonemes[-1].phoneme:
            phonemes[-1].phoneme = cls.space_phoneme
        return phonemes


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


class PhonemeType(str, Enum):
    jvs = "jvs"
    openjtalk = "openjtalk"


phoneme_type_to_class = {
    PhonemeType.jvs: JvsPhoneme,
    PhonemeType.openjtalk: OjtPhoneme,
}
