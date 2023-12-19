import re
from dataclasses import dataclass
from itertools import chain
from typing import Self

import pyopenjtalk


@dataclass
class Phoneme:
    """
    音素(母音・子音)クラス、音素の元となるcontextを保持する
    音素には、母音や子音以外にも無音(silent/pause)も含まれる

    Attributes
    ----------
    contexts: dict[str, str]
        音素の元
    """

    contexts: dict[str, str]

    @classmethod
    def from_label(cls, label: str):
        """
        pyopenjtalk.extract_fullcontextで得られる音素の元(ラベル)から、Phonemeクラスを作成する
        Parameters
        ----------
        label : str
            pyopenjtalk.extract_fullcontextで得られるラベルを渡す

        Returns
        -------
        phoneme: Phoneme
            Phonemeクラスを返す
        """

        # フルコンテキストラベルの仕様は、
        # http://hts.sp.nitech.ac.jp/?Download の HTS-2.3のJapanese tar.bz2 (126 MB)をダウンロードして、data/lab_format.pdfを見るとリストが見つかります。 # noqa
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
    def phoneme(self):
        """
        音素クラスの中で、発声に必要なcontextを返す
        Returns
        -------
        phoneme : str
            発声に必要なcontextを返す
        """
        return self.contexts["p3"]

    def is_pause(self):
        """
        音素がポーズ(無音、silent/pause)であるかを返す
        Returns
        -------
        is_pose : bool
            音素がポーズ(無音、silent/pause)であるか(True)否か(False)
        """
        return self.contexts["f1"] == "xx"

    def __repr__(self):
        return f"<Phoneme phoneme='{self.phoneme}'>"


@dataclass
class Mora:
    """
    モーラクラス
    モーラは1音素(母音や促音「っ」、撥音「ん」など)か、2音素(母音と子音の組み合わせ)で成り立つ

    Attributes
    ----------
    consonant : Phoneme | None
        子音
    vowel : Phoneme
        母音
    """

    consonant: Phoneme | None
    vowel: Phoneme

    def set_context(self, key: str, value: str):
        """
        Moraクラス内に含まれるPhonemeのcontextのうち、指定されたキーの値を変更する
        consonantが存在する場合は、vowelと同じようにcontextを変更する
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
        phonemes : list[Phoneme]
            母音しかない場合は母音のみ、子音もある場合は子音、母音の順番でPhonemeのリストを返す
        """
        if self.consonant is not None:
            return [self.consonant, self.vowel]
        else:
            return [self.vowel]


@dataclass
class AccentPhrase:
    """
    アクセント句クラス
    同じアクセントのMoraを複数保持する
    Attributes
    ----------
    moras : list[Mora]
        音韻のリスト
    accent : int
        アクセント
    """

    moras: list[Mora]
    accent: int
    is_interrogative: bool

    @classmethod
    def from_phonemes(cls, phonemes: list[Phoneme]) -> Self:
        """音素系列をcontextで区切りAccentPhraseインスタンスを生成する"""

        # NOTE:「モーラごとの音素系列」は音素系列をcontextで区切り生成される。

        moras: list[Mora] = []  # モーラ系列
        mora_phonemes: list[Phoneme] = []  # モーラごとの音素系列を一時保存するコンテナ

        for phoneme, next_phoneme in zip(phonemes, phonemes[1:] + [None]):
            # モーラ抽出を打ち切る（ワークアラウンド、VOICEVOX/voicevox_engine#57）
            # context a2（モーラ番号）の最大値が 49 であるため、49番目以降のモーラでは音素のモーラ番号を区切りに使えない
            if int(phoneme.contexts["a2"]) == 49:
                break

            # 区切りまで音素系列を一時保存する
            mora_phonemes.append(phoneme)

            # 一時的な音素系列を確定させて処理する
            # a2はアクセント句内でのモーラ番号(1~49)
            if (
                next_phoneme is None
                or phoneme.contexts["a2"] != next_phoneme.contexts["a2"]
            ):
                # モーラごとの音素系列長に基づいて子音と母音を得る
                if len(mora_phonemes) == 1:
                    consonant, vowel = None, mora_phonemes[0]
                elif len(mora_phonemes) == 2:
                    consonant, vowel = mora_phonemes[0], mora_phonemes[1]
                else:
                    raise ValueError(mora_phonemes)
                # 子音と母音からモーラを生成して保存する
                mora = Mora(consonant=consonant, vowel=vowel)
                moras.append(mora)
                # 次に向けてリセット
                mora_phonemes = []

        # アクセント位置を決定する
        # f2はアクセント句のアクセント位置(1~49)
        accent = int(moras[0].vowel.contexts["f2"])
        # f2 の値がアクセント句内のモーラ数を超える場合はクリップ（ワークアラウンド、VOICEVOX/voicevox_engine#55 を参照）
        accent = accent if accent <= len(moras) else len(moras)

        # 疑問文か否か判定する（末尾モーラ母音のcontextに基づく）
        # f3はアクセント句が疑問文かどうか（1で疑問文）
        is_interrogative = moras[-1].vowel.contexts["f3"] == "1"

        # AccentPhrase インスタンスを生成する
        accent_phrase = cls(
            moras=moras, accent=accent, is_interrogative=is_interrogative
        )

        return accent_phrase

    def set_context(self, key: str, value: str):
        """
        AccentPhraseに間接的に含まれる全てのPhonemeのcontextの、指定されたキーの値を変更する
        Parameters
        ----------
        key : str
            変更したいcontextのキー
        value : str
            変更したいcontextの値
        """
        for mora in self.moras:
            mora.set_context(key, value)

    @property
    def phonemes(self):
        """
        音素群を返す
        Returns
        -------
        phonemes : list[Phoneme]
            AccentPhraseに間接的に含まれる全てのPhonemeを返す
        """
        return list(chain.from_iterable(m.phonemes for m in self.moras))


@dataclass
class BreathGroup:
    """
    発声の区切りクラス
    アクセントの異なるアクセント句を複数保持する
    Attributes
    ----------
    accent_phrases : list[AccentPhrase]
        アクセント句のリスト
    """

    accent_phrases: list[AccentPhrase]

    @classmethod
    def from_phonemes(cls, phonemes: list[Phoneme]) -> Self:
        """音素系列をcontextで区切りBreathGroupインスタンスを生成する"""

        # NOTE:「アクセント句ごとの音素系列」は音素系列をcontextで区切り生成される。

        accent_phrases: list[AccentPhrase] = []  # アクセント句系列
        accent_phonemes: list[Phoneme] = []  # アクセント句ごとの音素系列を一時保存するコンテナ

        for phoneme, next_phoneme in zip(phonemes, phonemes[1:] + [None]):
            # 区切りまで音素系列を一時保存する
            accent_phonemes.append(phoneme)

            # 一時的な音素系列を確定させて処理する
            # i3はBreathGroupの番号
            # f5はBreathGroup内でのアクセント句の番号
            if (
                next_phoneme is None
                or phoneme.contexts["i3"] != next_phoneme.contexts["i3"]
                or phoneme.contexts["f5"] != next_phoneme.contexts["f5"]
            ):
                # アクセント句を生成して保存する
                accent_phrase = AccentPhrase.from_phonemes(accent_phonemes)
                accent_phrases.append(accent_phrase)
                # 次に向けてリセット
                accent_phonemes = []

        # BreathGroup インスタンスを生成する
        breath_group = cls(accent_phrases=accent_phrases)

        return breath_group

    def set_context(self, key: str, value: str):
        """
        BreathGroupに間接的に含まれる全てのPhonemeのcontextの、指定されたキーの値を変更する
        Parameters
        ----------
        key : str
            変更したいcontextのキー
        value : str
            変更したいcontextの値
        """
        for accent_phrase in self.accent_phrases:
            accent_phrase.set_context(key, value)

    @property
    def phonemes(self):
        """
        音素群を返す
        Returns
        -------
        phonemes : list[Phoneme]
            BreathGroupに間接的に含まれる全てのPhonemeを返す
        """
        return list(
            chain.from_iterable(
                accent_phrase.phonemes for accent_phrase in self.accent_phrases
            )
        )


@dataclass
class Utterance:
    """
    発声クラス
    発声の区切りと無音を複数保持する
    Attributes
    ----------
    breath_groups : list[BreathGroup]
        発声の区切りのリスト
    pauses : list[Phoneme]
        無音のリスト
    """

    breath_groups: list[BreathGroup]
    pauses: list[Phoneme]

    @classmethod
    def from_phonemes(cls, phonemes: list[Phoneme]) -> Self:
        """音素系列をポーズで区切りUtteranceインスタンスを生成する"""

        # NOTE:「BreathGroupごとの音素系列」は音素系列をポーズで区切り生成される。

        pauses: list[Phoneme] = []  # ポーズ音素のリスト
        breath_groups: list[BreathGroup] = []  # BreathGroup のリスト
        group_phonemes: list[Phoneme] = []  # BreathGroupごとの音素系列を一時保存するコンテナ

        for phoneme in phonemes:
            # ポーズが出現するまで音素系列を一時保存する
            if not phoneme.is_pause():
                group_phonemes.append(phoneme)

            # 一時的な音素系列を確定させて処理する
            else:
                # ポーズ音素を保存する
                pauses.append(phoneme)
                if len(group_phonemes) > 0:
                    # 音素系列からBreathGroupを生成して保存する
                    breath_group = BreathGroup.from_phonemes(group_phonemes)
                    breath_groups.append(breath_group)
                    # 次に向けてリセット
                    group_phonemes = []

        # Utteranceインスタンスを生成する
        utterance = cls(breath_groups=breath_groups, pauses=pauses)

        return utterance

    def set_context(self, key: str, value: str):
        """
        Utteranceに間接的に含まれる全てのPhonemeのcontextの、指定されたキーの値を変更する
        Parameters
        ----------
        key : str
            変更したいcontextのキー
        value : str
            変更したいcontextの値
        """
        for breath_group in self.breath_groups:
            breath_group.set_context(key, value)

    @property
    def phonemes(self):
        """
        音素群を返す
        Returns
        -------
        phonemes : list[Phoneme]
            Utteranceクラスに直接的・間接的に含まれる、全てのPhonemeを返す
        """
        phonemes: list[Phoneme] = []
        for i in range(len(self.pauses)):
            if self.pauses[i] is not None:
                phonemes += [self.pauses[i]]

            if i < len(self.pauses) - 1:
                phonemes += self.breath_groups[i].phonemes

        return phonemes


def extract_full_context_label(text: str):
    """
    日本語テキストから発話クラスを抽出
    Parameters
    ----------
    text : str
        日本語テキスト
    Returns
    -------
    utterance : Utterance
        発話
    """
    labels = pyopenjtalk.extract_fullcontext(text)
    phonemes = [Phoneme.from_label(label=label) for label in labels]
    utterance = Utterance.from_phonemes(phonemes)
    return utterance
