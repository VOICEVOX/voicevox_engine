import re
from dataclasses import dataclass
from itertools import chain
from typing import Dict, List, Optional

import pyopenjtalk


@dataclass
class Phoneme:
    contexts: Dict[str, str]

    @classmethod
    def from_label(cls, label: str):
        """
        pyopenjtalk.extract_fullcontextで得られる音素の元(ラベル)から、音素を作成する
        Parameters
        ----------
        label : str
            pyopenjtalk.extract_fullcontextで得られるラベルを入れる

        Returns
        -------
        phoneme: Phoneme
            Phoneme(音素)クラスを返す
        """
        contexts = re.search(
            r"^(?P<p1>.+?)\^(?P<p2>.+?)\-(?P<p3>.+?)\+(?P<p4>.+?)\=(?P<p5>.+?)"
            r"/A\:(?P<a1>.+?)\+(?P<a2>.+?)\+(?P<a3>.+?)"
            r"/B\:(?P<b1>.+?)\-(?P<b2>.+?)\_(?P<b3>.+?)"
            r"/C\:(?P<c1>.+?)\_(?P<c2>.+?)\+(?P<c3>.+?)"
            r"/D\:(?P<d1>.+?)\+(?P<d2>.+?)\_(?P<d3>.+?)"
            r"/E\:(?P<e1>.+?)\_(?P<e2>.+?)\!(?P<e3>.+?)\_(?P<e4>.+?)\-(?P<e5>.+?)"
            r"/F\:(?P<f1>.+?)\_(?P<f2>.+?)\#(?P<f3>.+?)\_(?P<f4>.+?)\@(?P<f5>.+?)\_(?P<f6>.+?)\|(?P<f7>.+?)\_(?P<f8>.+?)"  # noqa
            r"/G\:(?P<g1>.+?)\_(?P<g2>.+?)\%(?P<g3>.+?)\_(?P<g4>.+?)\_(?P<g5>.+?)"
            r"/H\:(?P<h1>.+?)\_(?P<h2>.+?)"
            r"/I\:(?P<i1>.+?)\-(?P<i2>.+?)\@(?P<i3>.+?)\+(?P<i4>.+?)\&(?P<i5>.+?)\-(?P<i6>.+?)\|(?P<i7>.+?)\+(?P<i8>.+?)"  # noqa
            r"/J\:(?P<j1>.+?)\_(?P<j2>.+?)"
            r"/K\:(?P<k1>.+?)\+(?P<k2>.+?)\-(?P<k3>.+?)$",
            label,
        ).groupdict()
        return cls(contexts=contexts)

    @property
    def label(self):
        """
        pyopenjtalk.extract_fullcontextで得られるラベルと等しい
        Returns
        -------
        lebel: str
            ラベルを返す
        """
        return (
            "{p1}^{p2}-{p3}+{p4}={p5}"
            "/A:{a1}+{a2}+{a3}"
            "/B:{b1}-{b2}_{b3}"
            "/C:{c1}_{c2}+{c3}"
            "/D:{d1}+{d2}_{d3}"
            "/E:{e1}_{e2}!{e3}_{e4}-{e5}"
            "/F:{f1}_{f2}#{f3}_{f4}@{f5}_{f6}|{f7}_{f8}"
            "/G:{g1}_{g2}%{g3}_{g4}_{g5}"
            "/H:{h1}_{h2}"
            "/I:{i1}-{i2}@{i3}+{i4}&{i5}-{i6}|{i7}+{i8}"
            "/J:{j1}_{j2}"
            "/K:{k1}+{k2}-{k3}"
        ).format(**self.contexts)

    @property
    def phoneme(self):
        """
        音素クラスの中で、発音すべきものを返す
        Returns
        -------
        phonome : str
            発音すべきものを返す
        """
        return self.contexts["p3"]

    def is_pose(self):
        """
        音素がポーズ(無音/silent)であるかを返す
        Returns
        -------
        is_pose : bool
            音素がポーズ(無音/silent)であるか(True)否か(False)
        """
        return self.contexts["f1"] == "xx"

    def __repr__(self):
        return f"<Phoneme phoneme='{self.phoneme}'>"


@dataclass
class Mora:
    consonant: Optional[Phoneme]
    vowel: Phoneme

    def set_context(self, key: str, value: str):
        """
        Mora(音韻)内に含まれるPhonemeのcontextを変更する
        consonant(子音)が存在する場合は、vowel(母音)と同じようにcontextを変更する
        Parameters
        ----------
        key : str
            変更したいcontextのキー
        value : str
            変更したいcontextの値
        """
        self.vowel.contexts[key] = value
        if self.consonant is not None:
            self.consonant.contexts[key] = value

    @property
    def phonemes(self):
        """
        音素群を返す
        Returns
        -------
        phonemes : List[Phoneme]
            母音しかない場合は母音のみ、子音もある場合は子音、母音の順番でPhonemeのリストを返す
        """
        if self.consonant is not None:
            return [self.consonant, self.vowel]
        else:
            return [self.vowel]

    @property
    def labels(self):
        """
        ラベル群を返す
        Returns
        -------
        labels : List[str]
            Moraに含まれるすべてのラベルを返す
        """
        return [p.label for p in self.phonemes]


@dataclass
class AccentPhrase:
    moras: List[Mora]
    accent: int

    @classmethod
    def from_phonemes(cls, phonemes: List[Phoneme]):
        moras: List[Mora] = []

        mora_phonemes: List[Phoneme] = []
        for phoneme, next_phoneme in zip(phonemes, phonemes[1:] + [None]):
            mora_phonemes.append(phoneme)

            if (
                next_phoneme is None
                or phoneme.contexts["a2"] != next_phoneme.contexts["a2"]
            ):
                if len(mora_phonemes) == 1:
                    consonant, vowel = None, mora_phonemes[0]
                elif len(mora_phonemes) == 2:
                    consonant, vowel = mora_phonemes[0], mora_phonemes[1]
                else:
                    raise ValueError(mora_phonemes)
                mora = Mora(consonant=consonant, vowel=vowel)
                moras.append(mora)
                mora_phonemes = []

        return cls(moras=moras, accent=int(moras[0].vowel.contexts["f2"]))

    def set_context(self, key: str, value: str):
        for mora in self.moras:
            mora.set_context(key, value)

    @property
    def phonemes(self):
        return list(chain.from_iterable(m.phonemes for m in self.moras))

    @property
    def labels(self):
        return [p.label for p in self.phonemes]

    def merge(self, accent_phrase: "AccentPhrase"):
        return AccentPhrase(
            moras=self.moras + accent_phrase.moras,
            accent=self.accent,
        )


@dataclass
class BreathGroup:
    accent_phrases: List[AccentPhrase]

    @classmethod
    def from_phonemes(cls, phonemes: List[Phoneme]):
        accent_phrases: List[AccentPhrase] = []
        accent_phonemes: List[Phoneme] = []
        for phoneme, next_phoneme in zip(phonemes, phonemes[1:] + [None]):
            accent_phonemes.append(phoneme)

            if (
                next_phoneme is None
                or phoneme.contexts["i3"] != next_phoneme.contexts["i3"]
                or phoneme.contexts["f5"] != next_phoneme.contexts["f5"]
            ):
                accent_phrase = AccentPhrase.from_phonemes(accent_phonemes)
                accent_phrases.append(accent_phrase)
                accent_phonemes = []

        return cls(accent_phrases=accent_phrases)

    def set_context(self, key: str, value: str):
        for accent_phrase in self.accent_phrases:
            accent_phrase.set_context(key, value)

    @property
    def phonemes(self):
        return list(
            chain.from_iterable(
                accent_phrase.phonemes for accent_phrase in self.accent_phrases
            )
        )

    @property
    def labels(self):
        return [p.label for p in self.phonemes]


@dataclass
class Utterance:
    breath_groups: List[BreathGroup]
    pauses: List[Phoneme]

    @classmethod
    def from_phonemes(cls, phonemes: List[Phoneme]):
        pauses: List[Phoneme] = []

        breath_groups: List[BreathGroup] = []
        group_phonemes: List[Phoneme] = []
        for phoneme in phonemes:
            if not phoneme.is_pose():
                group_phonemes.append(phoneme)

            else:
                pauses.append(phoneme)

                if len(group_phonemes) > 0:
                    breath_group = BreathGroup.from_phonemes(group_phonemes)
                    breath_groups.append(breath_group)
                    group_phonemes = []

        return cls(breath_groups=breath_groups, pauses=pauses)

    def set_context(self, key: str, value: str):
        for breath_group in self.breath_groups:
            breath_group.set_context(key, value)

    @property
    def phonemes(self):
        accent_phrases = list(
            chain.from_iterable(
                breath_group.accent_phrases for breath_group in self.breath_groups
            )
        )
        for prev, cent, post in zip(
            [None] + accent_phrases[:-1],
            accent_phrases,
            accent_phrases[1:] + [None],
        ):
            mora_num = len(cent.moras)
            accent = cent.accent

            if prev is not None:
                prev.set_context("g1", str(mora_num))
                prev.set_context("g2", str(accent))

            if post is not None:
                post.set_context("e1", str(mora_num))
                post.set_context("e2", str(accent))

            cent.set_context("f1", str(mora_num))
            cent.set_context("f2", str(accent))
            for i_mora, mora in enumerate(cent.moras):
                mora.set_context("a1", str(i_mora - accent + 1))
                mora.set_context("a2", str(i_mora + 1))
                mora.set_context("a3", str(mora_num - i_mora))

        for prev, cent, post in zip(
            [None] + self.breath_groups[:-1],
            self.breath_groups,
            self.breath_groups[1:] + [None],
        ):
            accent_phrase_num = len(cent.accent_phrases)

            if prev is not None:
                prev.set_context("j1", str(accent_phrase_num))

            if post is not None:
                post.set_context("h1", str(accent_phrase_num))

            cent.set_context("i1", str(accent_phrase_num))
            cent.set_context(
                "i5", str(accent_phrases.index(cent.accent_phrases[0]) + 1)
            )
            cent.set_context(
                "i6",
                str(len(accent_phrases) - accent_phrases.index(cent.accent_phrases[0])),
            )

        self.set_context(
            "k2",
            str(
                sum(
                    [
                        len(breath_group.accent_phrases)
                        for breath_group in self.breath_groups
                    ]
                )
            ),
        )

        phonemes: List[Phoneme] = []
        for i in range(len(self.pauses)):
            if self.pauses[i] is not None:
                phonemes += [self.pauses[i]]

            if i < len(self.pauses) - 1:
                phonemes += self.breath_groups[i].phonemes

        return phonemes

    @property
    def labels(self):
        return [p.label for p in self.phonemes]


def extract_full_context_label(text: str):
    labels = pyopenjtalk.extract_fullcontext(text)
    phonemes = [Phoneme.from_label(label=label) for label in labels]
    utterance = Utterance.from_phonemes(phonemes)
    return utterance
