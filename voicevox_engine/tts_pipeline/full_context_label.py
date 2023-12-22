import re
from dataclasses import dataclass
from itertools import chain
from typing import Self

import pyopenjtalk

from ..model import Mora, AccentPhrase
from .mora_list import openjtalk_mora2text


@dataclass
class Label:
    """
    OpenJTalk Label

    Attributes
    ----------
    contexts: dict[str, str]
        ラベルの属性
    """

    contexts: dict[str, str]

    @classmethod
    def from_feature(cls, feature: str):
        """OpenJTalk feature から Label インスタンスを生成する"""
        # フルコンテキストラベルの仕様は、http://hts.sp.nitech.ac.jp/?Download の HTS-2.3のJapanese tar.bz2 (126 MB)をダウンロードして、data/lab_format.pdfを見るとリストが見つかります。 # noqa
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
            feature,
        ).groupdict()
        return cls(contexts=contexts)

    @property
    def phoneme(self):
        """このラベルに含まれる音素。子音 or 母音 (無音含む)。"""
        return self.contexts["p3"]

    def is_pause(self):
        """このラベルが無音 (silent/pause) であれば True、そうでなければ False を返す"""
        return self.contexts["f1"] == "xx"

    def __repr__(self):
        return f"<Label phoneme='{self.phoneme}'>"


@dataclass
class MoraLabel:
    """
    モーラクラス
    モーラは1音素(母音や促音「っ」、撥音「ん」など)か、2音素(母音と子音の組み合わせ)で成り立つ

    Attributes
    ----------
    consonant : Label | None
        子音
    vowel : Label
        母音
    """

    consonant: Label | None
    vowel: Label

    def set_context(self, key: str, value: str):
        """
        Moraクラス内に含まれるLabelのcontextのうち、指定されたキーの値を変更する
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
        """このモーラを構成するラベルリスト。母音ラベルのみの場合は [母音ラベル,]、子音ラベルもある場合は [子音ラベル, 母音ラベル]。
        NOTE: `.labels` に名称変更予定
        """
        if self.consonant is not None:
            return [self.consonant, self.vowel]
        else:
            return [self.vowel]


@dataclass
class AccentPhraseLabel:
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

    moras: list[MoraLabel]
    accent: int
    is_interrogative: bool

    @classmethod
    def from_labels(cls, labels: list[Label]) -> Self:
        """ラベル系列をcontextで区切りAccentPhraseインスタンスを生成する"""

        # NOTE:「モーラごとのラベル系列」はラベル系列をcontextで区切り生成される。

        moras: list[MoraLabel] = []  # モーラ系列
        mora_labels: list[Label] = []  # モーラごとのラベル系列を一時保存するコンテナ

        for label, next_label in zip(labels, labels[1:] + [None]):
            # モーラ抽出を打ち切る（ワークアラウンド、VOICEVOX/voicevox_engine#57）
            # context a2（モーラ番号）の最大値が 49 であるため、49番目以降のモーラではラベルのモーラ番号を区切りに使えない
            if int(label.contexts["a2"]) == 49:
                break

            # 区切りまでラベル系列を一時保存する
            mora_labels.append(label)

            # 一時的なラベル系列を確定させて処理する
            # a2はアクセント句内でのモーラ番号(1~49)
            if next_label is None or label.contexts["a2"] != next_label.contexts["a2"]:
                # モーラごとのラベル系列長に基づいて子音と母音を得る
                if len(mora_labels) == 1:
                    consonant, vowel = None, mora_labels[0]
                elif len(mora_labels) == 2:
                    consonant, vowel = mora_labels[0], mora_labels[1]
                else:
                    raise ValueError(mora_labels)
                # 子音と母音からモーラを生成して保存する
                mora = MoraLabel(consonant=consonant, vowel=vowel)
                moras.append(mora)
                # 次に向けてリセット
                mora_labels = []

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
        AccentPhraseに間接的に含まれる全てのLabelのcontextの、指定されたキーの値を変更する
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
        内包する全てのラベルを返す
        NOTE: `.labels` に名称変更予定
        Returns
        -------
        labels : list[Label]
            AccentPhraseに間接的に含まれる全てのLabelを返す
        """
        return list(chain.from_iterable(m.phonemes for m in self.moras))


@dataclass
class BreathGroupLabel:
    """
    発声の区切りクラス
    アクセントの異なるアクセント句を複数保持する
    Attributes
    ----------
    accent_phrases : list[AccentPhrase]
        アクセント句のリスト
    """

    accent_phrases: list[AccentPhraseLabel]

    @classmethod
    def from_labels(cls, labels: list[Label]) -> Self:
        """ラベル系列をcontextで区切りBreathGroupインスタンスを生成する"""

        # NOTE:「アクセント句ごとのラベル系列」はラベル系列をcontextで区切り生成される。

        accent_phrases: list[AccentPhraseLabel] = []  # アクセント句系列
        accent_labels: list[Label] = []  # アクセント句ごとのラベル系列を一時保存するコンテナ

        for label, next_label in zip(labels, labels[1:] + [None]):
            # 区切りまでラベル系列を一時保存する
            accent_labels.append(label)

            # 一時的なラベル系列を確定させて処理する
            # i3はBreathGroupの番号
            # f5はBreathGroup内でのアクセント句の番号
            if (
                next_label is None
                or label.contexts["i3"] != next_label.contexts["i3"]
                or label.contexts["f5"] != next_label.contexts["f5"]
            ):
                # アクセント句を生成して保存する
                accent_phrase = AccentPhraseLabel.from_labels(accent_labels)
                accent_phrases.append(accent_phrase)
                # 次に向けてリセット
                accent_labels = []

        # BreathGroup インスタンスを生成する
        breath_group = cls(accent_phrases=accent_phrases)

        return breath_group

    def set_context(self, key: str, value: str):
        """
        BreathGroupに間接的に含まれる全てのLabelのcontextの、指定されたキーの値を変更する
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
        内包する全てのラベルを返す
        NOTE: `.labels` に名称変更予定
        Returns
        -------
        labels : list[Label]
            BreathGroupに間接的に含まれる全てのLabelを返す
        """
        return list(
            chain.from_iterable(
                accent_phrase.phonemes for accent_phrase in self.accent_phrases
            )
        )


@dataclass
class UtteranceLabel:
    """
    発声クラス
    発声の区切りと無音を複数保持する
    Attributes
    ----------
    breath_groups : list[BreathGroup]
        発声の区切りのリスト
    pauses : list[Label]
        無音のリスト
    """

    breath_groups: list[BreathGroupLabel]
    pauses: list[Label]

    @classmethod
    def from_labels(cls, labels: list[Label]) -> Self:
        """ラベル系列をポーズで区切りUtteranceインスタンスを生成する"""

        # NOTE:「BreathGroupごとのラベル系列」はラベル系列をポーズで区切り生成される。

        pauses: list[Label] = []  # ポーズラベルのリスト
        breath_groups: list[BreathGroupLabel] = []  # BreathGroup のリスト
        group_labels: list[Label] = []  # BreathGroupごとのラベル系列を一時保存するコンテナ

        for label in labels:
            # ポーズが出現するまでラベル系列を一時保存する
            if not label.is_pause():
                group_labels.append(label)

            # 一時的なラベル系列を確定させて処理する
            else:
                # ポーズラベルを保存する
                pauses.append(label)
                if len(group_labels) > 0:
                    # ラベル系列からBreathGroupを生成して保存する
                    breath_group = BreathGroupLabel.from_labels(group_labels)
                    breath_groups.append(breath_group)
                    # 次に向けてリセット
                    group_labels = []

        # Utteranceインスタンスを生成する
        utterance = cls(breath_groups=breath_groups, pauses=pauses)

        return utterance

    def set_context(self, key: str, value: str):
        """
        Utteranceに間接的に含まれる全てのLabelのcontextの、指定されたキーの値を変更する
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
        内包する全てのラベルを返す
        NOTE: `.labels` に名称変更予定
        Returns
        -------
        labels : list[Label]
            Utteranceクラスに直接的・間接的に含まれる、全てのLabelを返す
        """
        labels: list[Label] = []
        for i in range(len(self.pauses)):
            if self.pauses[i] is not None:
                labels += [self.pauses[i]]

            if i < len(self.pauses) - 1:
                labels += self.breath_groups[i].phonemes

        return labels


def _extract_utterance_label(text: str) -> UtteranceLabel:
    """日本語文からUtteranceLabelを抽出する"""
    features: list[str] = pyopenjtalk.extract_fullcontext(text) #type: ignore
    labels = [Label.from_feature(feature) for feature in features]
    utterance = UtteranceLabel.from_labels(labels)
    return utterance


def mora_to_text(mora: str) -> str:
    """
    Parameters
    ----------
    mora : str
        モーラ音素文字列
    Returns
    -------
    mora : str
        モーラ音素文字列
    """
    if mora[-1:] in ["A", "I", "U", "E", "O"]:
        # 無声化母音を小文字に
        mora = mora[:-1] + mora[-1].lower()
    if mora in openjtalk_mora2text:
        return openjtalk_mora2text[mora]
    else:
        return mora


def _mora_labels_to_moras(mora_labels: list[MoraLabel]) -> list[Mora]:
    """MoraLabel系列をMora系列へキャストする。音素長と音高は 0 初期化"""
    return [
        Mora(
            text=mora_to_text("".join([p.phoneme for p in mora.phonemes])),
            consonant=(mora.consonant.phoneme if mora.consonant is not None else None),
            consonant_length=0 if mora.consonant is not None else None,
            vowel=mora.vowel.phoneme,
            vowel_length=0,
            pitch=0,
        )
        for mora in mora_labels
    ]


def _utterance_to_accent_phrases(utterance: UtteranceLabel) -> list[AccentPhrase]:
    """UtteranceLabelインスタンスをアクセント句系列へドメイン変換する"""
    return [
        AccentPhrase(
            moras=_mora_labels_to_moras(accent_phrase.moras),
            accent=accent_phrase.accent,
            pause_mora=(
                Mora(
                    text="、",
                    consonant=None,
                    consonant_length=None,
                    vowel="pau",
                    vowel_length=0,
                    pitch=0,
                )
                if (
                    i_accent_phrase == len(breath_group.accent_phrases) - 1
                    and i_breath_group != len(utterance.breath_groups) - 1
                )
                else None
            ),
            is_interrogative=accent_phrase.is_interrogative,
        )
        for i_breath_group, breath_group in enumerate(utterance.breath_groups)
        for i_accent_phrase, accent_phrase in enumerate(breath_group.accent_phrases)
    ]


def text_to_accent_phrases(text: str) -> list[AccentPhrase]:
    """日本語文からアクセント句系列を生成する"""
    if len(text.strip()) == 0:
        return []

    # 日本語文からUtteranceLabelを抽出する
    utterance = _extract_utterance_label(text)
    if len(utterance.breath_groups) == 0:
        return []

    # ドメインを変換する
    return _utterance_to_accent_phrases(utterance)
