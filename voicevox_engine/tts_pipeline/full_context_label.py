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
        音素クラスの中で、発声に必要な要素を返す
        Returns
        -------
        phoneme : str
            発声に必要な要素を返す
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

    @property
    def labels(self):
        """
        ラベル群を返す
        Returns
        -------
        labels : list[str]
            Moraに含まれるすべてのラベルを返す
        """
        return [p.label for p in self.phonemes]


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
        """音素系列をコンテキスト値で区切り AccentPhrase インスタンスを生成する"""

        # NOTE:「音素サブ系列」は単一モーラを構成する音素系列である。音素系列をコンテキスト値で区切り生成される。

        moras: list[Mora] = []  # 音素サブ行列から生成されたモーラ系列
        mora_phonemes: list[Phoneme] = []  # 音素サブ系列を一時保存するコンテナ

        for phoneme, next_phoneme in zip(phonemes, phonemes[1:] + [None]):
            # モーラ抽出を打ち切る（ワークアラウンド、VOICEVOX/voicevox_engine#57）
            # (py)openjtalk コンテキスト a2 属性（モーラ番号）の最大値が 49 であるため、49番目以降のモーラでは音素のモーラ番号を区切りに使えない
            if int(phoneme.contexts["a2"]) == 49:
                break

            # 区切りとなるコンテキスト値が出現するまで音素サブ系列の一員として一時保存する
            mora_phonemes.append(phoneme)

            # 確定した音素サブ系列を処理する
            # コンテキスト a2 属性の定義: "position of the current mora identity in the current accent phrase (forward)    1 ~ 49"  # noqa: B950
            if (
                next_phoneme is None
                or phoneme.contexts["a2"] != next_phoneme.contexts["a2"]
            ):
                # 音素サブ系列長に基づいて子音と母音を得る
                if len(mora_phonemes) == 1:
                    consonant, vowel = None, mora_phonemes[0]
                elif len(mora_phonemes) == 2:
                    consonant, vowel = mora_phonemes[0], mora_phonemes[1]
                else:
                    raise ValueError(mora_phonemes)
                # 子音と母音からモーラを生成して保存する
                mora = Mora(consonant=consonant, vowel=vowel)
                moras.append(mora)
                # 音素サブ行列コンテナを初期化する
                mora_phonemes = []

        # アクセント位置を決定する
        # コンテキスト f2 属性の定義: "accent type in the current accent phrase    1 ~ 49"
        accent = int(moras[0].vowel.contexts["f2"])
        # f2 の値がアクセント句内のモーラ数を超える場合はクリップ（ワークアラウンド、VOICEVOX/voicevox_engine#55 を参照）
        accent = accent if accent <= len(moras) else len(moras)

        # 疑問文か否か判定する（末尾モーラ母音のコンテキスト値に基づく）
        # コンテキスト f3 属性の定義: "whether the current accent phrase interrogative or not (0: not interrogative, 1: interrogative)"  # noqa: B950
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

    @property
    def labels(self):
        """
        ラベル群を返す
        Returns
        -------
        labels : list[str]
            AccentPhraseに間接的に含まれる全てのラベルを返す
        """
        return [p.label for p in self.phonemes]

    def merge(self, accent_phrase: "AccentPhrase"):
        """
        AccentPhraseを合成する
        (このクラスが保持するmorasの後ろに、引数として渡されたAccentPhraseのmorasを合成する)
        Parameters
        ----------
        accent_phrase : AccentPhrase
            合成したいAccentPhraseを渡す

        Returns
        -------
        accent_phrase : AccentPhrase
            合成されたAccentPhraseを返す
        """
        return AccentPhrase(
            moras=self.moras + accent_phrase.moras,
            accent=self.accent,
            is_interrogative=accent_phrase.is_interrogative,
        )


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
        """音素系列をコンテキスト値で区切り BreathGroup インスタンスを生成する"""

        # NOTE:「音素サブ系列」は単一アクセント句を構成する音素系列である。音素系列をコンテキスト値で区切り生成される。

        accent_phrases: list[AccentPhrase] = []  # 音素サブ行列から生成されたアクセント句系列
        accent_phonemes: list[Phoneme] = []  # 音素サブ系列を一時保存するコンテナ

        for phoneme, next_phoneme in zip(phonemes, phonemes[1:] + [None]):
            # 区切りとなるコンテキスト値が出現するまで音素サブ系列の一員として一時保存する
            accent_phonemes.append(phoneme)

            # 確定した音素サブ系列を処理する
            # コンテキスト i3 属性の定義: "position of the current breath group identity by breath group (forward)"  # noqa: B950
            # コンテキスト f5 属性の定義: "position of the current accent phrase identity in the current breath group by the accent phrase (forward)"  # noqa: B950
            if (
                next_phoneme is None
                or phoneme.contexts["i3"] != next_phoneme.contexts["i3"]
                or phoneme.contexts["f5"] != next_phoneme.contexts["f5"]
            ):
                # 音素サブ系列からアクセント句を生成して保存する
                accent_phrase = AccentPhrase.from_phonemes(accent_phonemes)
                accent_phrases.append(accent_phrase)
                # 音素サブ行列コンテナを初期化する
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

    @property
    def labels(self):
        """
        ラベル群を返す
        Returns
        -------
        labels : list[str]
            BreathGroupに間接的に含まれる全てのラベルを返す
        """
        return [p.label for p in self.phonemes]


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
        """音素系列をポーズで区切り Utterance インスタンスを生成する"""

        # NOTE:「音素サブ系列」は単一 BreathGroup を構成する音素系列である。音素系列をポーズで区切り生成される。

        pauses: list[Phoneme] = []  # ポーズ音素のリスト
        breath_groups: list[BreathGroup] = []  # 音素サブ行列から生成された BreathGroup のリスト
        group_phonemes: list[Phoneme] = []  # 音素サブ系列を一時保存するコンテナ

        for phoneme in phonemes:
            # ポーズが出現するまで音素サブ系列の一員として一時保存する
            if not phoneme.is_pause():
                group_phonemes.append(phoneme)

            # 確定した音素サブ系列を処理する
            else:
                # ポーズ音素を保存する
                pauses.append(phoneme)
                if len(group_phonemes) > 0:
                    # 音素サブ系列から BreathGroup を生成して保存する
                    breath_group = BreathGroup.from_phonemes(group_phonemes)
                    breath_groups.append(breath_group)
                    # 音素サブ行列コンテナを初期化する
                    group_phonemes = []

        # Utterance インスタンスを生成する
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

        phonemes: list[Phoneme] = []
        for i in range(len(self.pauses)):
            if self.pauses[i] is not None:
                phonemes += [self.pauses[i]]

            if i < len(self.pauses) - 1:
                phonemes += self.breath_groups[i].phonemes

        return phonemes

    @property
    def labels(self):
        """
        ラベル群を返す
        Returns
        -------
        labels : list[str]
            Utteranceクラスに直接的・間接的に含まれる全てのラベルを返す
        """
        return [p.label for p in self.phonemes]


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
