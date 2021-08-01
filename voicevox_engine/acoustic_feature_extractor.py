from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Sequence

import numpy


@dataclass
class SamplingData:
    array: numpy.ndarray  # shape: (N, ?)
    rate: float

    def resample(self, sampling_rate: float, index: int = 0, length: int = None):
        if length is None:
            length = int(len(self.array) / self.rate * sampling_rate)
        indexes = (numpy.random.rand() + index + numpy.arange(length)) * (
            self.rate / sampling_rate
        )
        return self.array[indexes.astype(int)]


class BasePhoneme(object):
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
        assert self.phoneme in self.phoneme_list, f"{self.phoneme} is not defined."

    @property
    def phoneme_id(self):
        return self.phoneme_list.index(self.phoneme)

    @property
    def duration(self):
        return self.end - self.start

    @property
    def onehot(self):
        array = numpy.zeros(self.num_phoneme, dtype=bool)
        array[self.phoneme_id] = True
        return array

    @classmethod
    def parse(cls, s: str):
        """
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
        pass

    @classmethod
    def load_julius_list(cls, path: Path):
        phonemes = [cls.parse(s) for s in path.read_text().split("\n") if len(s) > 0]
        phonemes = cls.convert(phonemes)

        for phoneme in phonemes:
            phoneme.verify()
        return phonemes

    @classmethod
    def save_julius_list(cls, phonemes: List["BasePhoneme"], path: Path):
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
    def convert(cls, phonemes: List["JvsPhoneme"]):
        if "sil" in phonemes[0].phoneme:
            phonemes[0].phoneme = cls.space_phoneme
        if "sil" in phonemes[-1].phoneme:
            phonemes[-1].phoneme = cls.space_phoneme
        return phonemes


class OjtPhoneme(BasePhoneme):
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
