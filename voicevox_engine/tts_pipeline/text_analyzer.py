"""テキスト解析"""

import re
from dataclasses import dataclass
from itertools import groupby
from typing import Any, Final, Literal, Self, TypeGuard

from .model import AccentPhrase, Mora
from .mora_mapping import mora_phonemes_to_mora_kana
from .phoneme import Consonant, Sil, Vowel


class NonOjtPhonemeError(Exception):
    """OpenJTalk で想定されていない音素が検出された。"""

    def __init__(self, **kwargs: Any) -> None:
        self.text = "OpenJTalk で想定されていない音素が生成されたため処理できません。"


class OjtUnknownPhonemeError(Exception):
    """OpenJTalk の unknown 音素 `xx` が検出された。"""

    def __init__(self, **kwargs: Any) -> None:
        self.text = "OpenJTalk の unknown 音素 `xx` は非対応です。"


_OJT_UNKNOWN = Literal["xx"]

# OpenJTalk が出力する音素の一覧。
_OJT_VOWELS: Final[tuple[Vowel | Sil, ...]] = (
    "A",
    "E",
    "I",
    "N",
    "O",
    "U",
    "a",
    "cl",
    "e",
    "i",
    "o",
    "pau",
    "sil",
    "u",
)
_OJT_CONSONANTS: Final[tuple[Consonant, ...]] = (
    "b",
    "by",
    "ch",
    "d",
    "dy",
    "f",
    "g",
    "gw",
    "gy",
    "h",
    "hy",
    "j",
    "k",
    "kw",
    "ky",
    "m",
    "my",
    "n",
    "ny",
    "p",
    "py",
    "r",
    "ry",
    "s",
    "sh",
    "t",
    "ts",
    "ty",
    "v",
    "w",
    "y",
    "z",
)
_OJT_UNKNOWNS: Final[tuple[_OJT_UNKNOWN]] = ("xx",)
_OJT_PHONEMES: Final = _OJT_VOWELS + _OJT_CONSONANTS + _OJT_UNKNOWNS


def _is_ojt_phoneme(
    p: str,
) -> TypeGuard[Vowel | Sil | Consonant | _OJT_UNKNOWN]:
    return p in _OJT_PHONEMES


@dataclass(frozen=True)
class _Label:
    """フルコンテキストラベルのサブセット。"""

    phoneme: Vowel | Consonant | Sil  # 音素。子音か母音 (無音含む)。
    is_pause: bool  # 無音 (silent/pause) か否か。
    mora_index: int | None  # アクセント句内におけるモーラのインデックス (1 ~ 49)。
    accent_position: int | None  # アクセント句内におけるアクセントの位置 (1 ~ 49)。
    is_interrogative: bool  # 疑問形か否か。
    accent_phrase_index: str  # BreathGroup内におけるアクセント句のインデックス。
    breath_group_index: str  # BreathGroupのインデックス。
    # TODO: accent_phrase_index と breath_group_index が str である理由を明記する or 修正する。

    @classmethod
    def from_feature(cls, feature: str) -> Self:
        """OpenJTalk feature から _Label インスタンスを生成する"""
        # フルコンテキストラベルの仕様は、http://hts.sp.nitech.ac.jp/?Download の HTS-2.3のJapanese tar.bz2 (126 MB)をダウンロードして、data/lab_format.pdfを見るとリストが見つかります。
        # VOICEVOX ENGINE で利用されている属性: p3 phoneme / a2 moraIdx / f1 n_mora / f2 pos_accent / f3 疑問形 / f5 アクセント句Idx / i3 BreathGroupIdx
        result = re.search(
            r"^(?P<p1>.+?)\^(?P<p2>.+?)\-(?P<p3>.+?)\+(?P<p4>.+?)\=(?P<p5>.+?)"
            r"/A\:(?P<a1>.+?)\+(?P<a2>.+?)\+(?P<a3>.+?)"
            r"/B\:(?P<b1>.+?)\-(?P<b2>.+?)\_(?P<b3>.+?)"
            r"/C\:(?P<c1>.+?)\_(?P<c2>.+?)\+(?P<c3>.+?)"
            r"/D\:(?P<d1>.+?)\+(?P<d2>.+?)\_(?P<d3>.+?)"
            r"/E\:(?P<e1>.+?)\_(?P<e2>.+?)\!(?P<e3>.+?)\_(?P<e4>.+?)\-(?P<e5>.+?)"
            r"/F\:(?P<f1>.+?)\_(?P<f2>.+?)\#(?P<f3>.+?)\_(?P<f4>.+?)\@(?P<f5>.+?)\_(?P<f6>.+?)\|(?P<f7>.+?)\_(?P<f8>.+?)"
            r"/G\:(?P<g1>.+?)\_(?P<g2>.+?)\%(?P<g3>.+?)\_(?P<g4>.+?)\_(?P<g5>.+?)"
            r"/H\:(?P<h1>.+?)\_(?P<h2>.+?)"
            r"/I\:(?P<i1>.+?)\-(?P<i2>.+?)\@(?P<i3>.+?)\+(?P<i4>.+?)\&(?P<i5>.+?)\-(?P<i6>.+?)\|(?P<i7>.+?)\+(?P<i8>.+?)"
            r"/J\:(?P<j1>.+?)\_(?P<j2>.+?)"
            r"/K\:(?P<k1>.+?)\+(?P<k2>.+?)\-(?P<k3>.+?)$",
            feature,
        )
        if result is None:
            raise ValueError(feature)
        contexts = result.groupdict()

        # 音素をバリデーションする
        p = contexts["p3"]
        if _is_ojt_phoneme(p):
            if p == "xx":
                raise OjtUnknownPhonemeError()
        else:
            raise NonOjtPhonemeError()

        # NOTE: pau と sil はアクセント句に属さないため、モーラインデックスが無い
        _mora_index = contexts["a2"]
        if _mora_index == "xx":
            mora_index = None
        else:
            mora_index = int(_mora_index)

        # NOTE: pau と sil はアクセント句に属さないため、アクセント位置が無い
        _accent_position = contexts["f2"]
        if _accent_position == "xx":
            accent_position = None
        else:
            accent_position = int(_accent_position)

        return cls(
            phoneme=p,
            is_pause=contexts["f1"] == "xx",
            mora_index=mora_index,
            accent_position=accent_position,
            is_interrogative=contexts["f3"] == "1",
            accent_phrase_index=contexts["f5"],
            breath_group_index=contexts["i3"],
        )


@dataclass
class _MoraLabel:
    """モーララベル。モーラは1音素(母音や促音「っ」、撥音「ん」など)か、2音素(母音と子音の組み合わせ)で成り立つ。"""

    consonant: _Label | None  # 子音
    vowel: _Label  # 母音

    @property
    def labels(self) -> list[_Label]:
        """このモーラを構成するラベルリスト。母音ラベルのみの場合は [母音ラベル,]、子音ラベルもある場合は [子音ラベル, 母音ラベル]。"""
        if self.consonant is not None:
            return [self.consonant, self.vowel]
        else:
            return [self.vowel]


@dataclass
class _AccentPhraseLabel:
    """アクセント句ラベル"""

    moras: list[_MoraLabel]  # モーラ系列
    accent: int  # アクセント位置
    is_interrogative: bool  # 疑問文か否か

    @classmethod
    def from_labels(cls, labels: list[_Label]) -> Self:
        """ラベル系列をcontextで区切りアクセント句ラベルを生成する"""
        # NOTE:「モーラごとのラベル系列」はラベル系列をcontextで区切り生成される。

        moras: list[_MoraLabel] = []  # モーラ系列
        for mora_index, _mora_labels in groupby(labels, lambda label: label.mora_index):
            mora_labels = list(_mora_labels)

            # モーラ抽出を打ち切る（ワークアラウンド、VOICEVOX/voicevox_engine#57）
            # mora_index の最大値が 49 であるため、49番目以降のモーラではラベルのモーラ番号を区切りに使えない
            if mora_index is not None and mora_index >= 49:
                break

            # ラベルの数に基づいて子音と母音を分け、モーラを生成する
            match len(mora_labels):
                case 1:
                    consonant, vowel = None, mora_labels[0]
                case 2:
                    consonant, vowel = mora_labels[0], mora_labels[1]
                case _:
                    raise ValueError(mora_labels)
            moras.append(_MoraLabel(consonant=consonant, vowel=vowel))

        # アクセント位置を決定する
        _accent = moras[0].vowel.accent_position
        if _accent is None:
            msg = "アクセント位置が指定されていません。"
            raise RuntimeError(msg)
        # アクセント位置の値がアクセント句内のモーラ数を超える場合はクリップ（ワークアラウンド、VOICEVOX/voicevox_engine#55 を参照）
        accent = _accent if _accent <= len(moras) else len(moras)

        # 疑問文か否か判定する（末尾モーラ母音のcontextに基づく）
        is_interrogative = moras[-1].vowel.is_interrogative

        # アクセント句ラベルを生成する
        accent_phrase = cls(
            moras=moras, accent=accent, is_interrogative=is_interrogative
        )

        return accent_phrase


@dataclass
class _BreathGroupLabel:
    """発声区切りラベル"""

    accent_phrases: list[_AccentPhraseLabel]  # アクセント句のリスト

    @classmethod
    def from_labels(cls, labels: list[_Label]) -> Self:
        """ラベル系列をcontextで区切りBreathGroupLabelインスタンスを生成する"""
        groups = groupby(
            labels,
            lambda label: (label.breath_group_index, label.accent_phrase_index),
        )
        accent_phrases = [
            _AccentPhraseLabel.from_labels(list(labels)) for _, labels in groups
        ]
        return cls(accent_phrases=accent_phrases)


@dataclass
class _UtteranceLabel:
    """発声ラベル"""

    breath_groups: list[_BreathGroupLabel]  # 発声の区切りのリスト

    @classmethod
    def from_labels(cls, labels: list[_Label]) -> Self:
        """ラベル系列をポーズで区切りUtteranceLabelインスタンスを生成する"""
        return cls(
            breath_groups=[
                _BreathGroupLabel.from_labels(list(labels))
                for is_pau, labels in groupby(labels, lambda label: label.is_pause)
                if not is_pau
            ]
        )


def mora_to_text(mora_phonemes: str) -> str:
    """モーラ相当の音素文字系列を日本語カタカナ文へ変換する（例: 'hO' -> 'ホ')"""
    if mora_phonemes[-1:] in ["A", "I", "U", "E", "O"]:
        # 無声化母音を小文字に
        mora_phonemes = mora_phonemes[:-1] + mora_phonemes[-1].lower()
    if mora_phonemes in mora_phonemes_to_mora_kana:
        return mora_phonemes_to_mora_kana[mora_phonemes]
    else:
        return mora_phonemes


def _mora_labels_to_moras(mora_labels: list[_MoraLabel]) -> list[Mora]:
    """
    MoraLabel系列をMora系列へキャストする。

    音素長と音高は0で初期化する。
    """
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


def full_context_labels_to_accent_phrases(
    full_context_labels: list[str],
) -> list[AccentPhrase]:
    """フルコンテキストラベルからアクセント句系列を生成する"""
    if len(full_context_labels) == 0:
        return []

    utterance = _UtteranceLabel.from_labels(
        list(map(_Label.from_feature, full_context_labels))
    )

    # _UtteranceLabelインスタンスからアクセント句系列を生成する。
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
