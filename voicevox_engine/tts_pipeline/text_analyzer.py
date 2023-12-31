import re
from dataclasses import dataclass
from itertools import chain
from typing import Self

import pyopenjtalk

from ..model import AccentPhrase, AccentPhrases, Mora
from .mora_list import openjtalk_mora2text


@dataclass
class Label:
    """OpenJTalkラベル"""

    contexts: dict[str, str]  # ラベルの属性

    @classmethod
    def from_feature(cls, feature: str) -> Self:
        """OpenJTalk feature から Label インスタンスを生成する"""
        # フルコンテキストラベルの仕様は、http://hts.sp.nitech.ac.jp/?Download の HTS-2.3のJapanese tar.bz2 (126 MB)をダウンロードして、data/lab_format.pdfを見るとリストが見つかります。 # noqa
        result = re.search(
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
        )
        if result is None:
            raise ValueError(feature)

        contexts = result.groupdict()
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
    """モーララベル。モーラは1音素(母音や促音「っ」、撥音「ん」など)か、2音素(母音と子音の組み合わせ)で成り立つ。"""

    consonant: Label | None  # 子音
    vowel: Label  # 母音

    @property
    def labels(self) -> list[Label]:
        """このモーラを構成するラベルリスト。母音ラベルのみの場合は [母音ラベル,]、子音ラベルもある場合は [子音ラベル, 母音ラベル]。"""
        if self.consonant is not None:
            return [self.consonant, self.vowel]
        else:
            return [self.vowel]


@dataclass
class AccentPhraseLabel:
    """アクセント句ラベル"""

    moras: list[MoraLabel]  # モーラ系列
    accent: int  # アクセント位置
    is_interrogative: bool  # 疑問文か否か

    @classmethod
    def from_labels(cls, labels: list[Label]) -> Self:
        """ラベル系列をcontextで区切りアクセント句ラベルを生成する"""

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

        # アクセント句ラベルを生成する
        accent_phrase = cls(
            moras=moras, accent=accent, is_interrogative=is_interrogative
        )

        return accent_phrase

    @property
    def labels(self) -> list[Label]:
        """内包する全てのラベルを返す"""
        return list(chain.from_iterable(m.labels for m in self.moras))


@dataclass
class BreathGroupLabel:
    """発声区切りラベル"""

    accent_phrases: list[AccentPhraseLabel]  # アクセント句のリスト

    @classmethod
    def from_labels(cls, labels: list[Label]) -> Self:
        """ラベル系列をcontextで区切りBreathGroupLabelインスタンスを生成する"""

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

        # BreathGroupLabel インスタンスを生成する
        breath_group = cls(accent_phrases=accent_phrases)

        return breath_group

    @property
    def labels(self) -> list[Label]:
        """内包する全てのラベルを返す"""
        return list(
            chain.from_iterable(
                accent_phrase.labels for accent_phrase in self.accent_phrases
            )
        )


@dataclass
class UtteranceLabel:
    """発声ラベル"""

    breath_groups: list[BreathGroupLabel]  # 発声の区切りのリスト
    pauses: list[Label]  # 無音のリスト

    @classmethod
    def from_labels(cls, labels: list[Label]) -> Self:
        """ラベル系列をポーズで区切りUtteranceLabelインスタンスを生成する"""

        # NOTE:「BreathGroupLabelごとのラベル系列」はラベル系列をポーズで区切り生成される。

        pauses: list[Label] = []  # ポーズラベルのリスト
        breath_groups: list[BreathGroupLabel] = []  # BreathGroupLabel のリスト
        group_labels: list[Label] = []  # BreathGroupLabelごとのラベル系列を一時保存するコンテナ

        for label in labels:
            # ポーズが出現するまでラベル系列を一時保存する
            if not label.is_pause():
                group_labels.append(label)

            # 一時的なラベル系列を確定させて処理する
            else:
                # ポーズラベルを保存する
                pauses.append(label)
                if len(group_labels) > 0:
                    # ラベル系列からBreathGroupLabelを生成して保存する
                    breath_group = BreathGroupLabel.from_labels(group_labels)
                    breath_groups.append(breath_group)
                    # 次に向けてリセット
                    group_labels = []

        # UtteranceLabelインスタンスを生成する
        utterance = cls(breath_groups=breath_groups, pauses=pauses)

        return utterance

    @property
    def labels(self) -> list[Label]:
        """内包する全てのラベルを返す"""
        labels: list[Label] = []
        for i in range(len(self.pauses)):
            if self.pauses[i] is not None:
                labels += [self.pauses[i]]

            if i < len(self.pauses) - 1:
                labels += self.breath_groups[i].labels

        return labels


def mora_to_text(mora: str) -> str:
    """モーラ相当の音素文字系列を日本語カタカナ文へ変換する（例: 'hO' -> 'ホ')"""
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
            text=mora_to_text("".join([label.phoneme for label in mora.labels])),
            consonant=(mora.consonant.phoneme if mora.consonant is not None else None),
            consonant_length=0 if mora.consonant is not None else None,
            vowel=mora.vowel.phoneme,
            vowel_length=0,
            pitch=0,
        )
        for mora in mora_labels
    ]


def _utterance_to_accent_phrases(utterance: UtteranceLabel) -> AccentPhrases:
    """UtteranceLabelインスタンスをアクセント句系列へドメイン変換する"""
    if len(utterance.breath_groups) == 0:
        return []

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


def text_to_accent_phrases(text: str) -> AccentPhrases:
    """日本語文からアクセント句系列を生成する"""
    if len(text.strip()) == 0:
        return []

    # 日本語文からUtteranceLabelを抽出する
    features: list[str] = pyopenjtalk.extract_fullcontext(text)  # type: ignore
    utterance = UtteranceLabel.from_labels(list(map(Label.from_feature, features)))

    # ドメインを変換する
    accent_phrases = _utterance_to_accent_phrases(utterance)

    return accent_phrases
