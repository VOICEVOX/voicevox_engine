"""テキスト解析"""

import re
from dataclasses import dataclass
from itertools import groupby
from typing import Any, Final, Literal, Self, TypeAlias, TypeGuard

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


def _generate_mora(consonant: _Label | None, vowel: _Label) -> Mora:
    """音素長と音高を0で初期化したモーラを生成する。"""
    phonemes = vowel.phoneme if consonant is None else consonant.phoneme + vowel.phoneme
    return Mora(
        text=mora_to_text(phonemes),
        consonant=(consonant.phoneme if consonant is not None else None),
        consonant_length=0 if consonant is not None else None,
        vowel=vowel.phoneme,
        vowel_length=0,
        pitch=0,
    )


def _generate_pau_mora() -> Mora:
    """音素長と音高を0で初期化したpauモーラを生成する。"""
    return Mora(
        text="、",
        consonant=None,
        consonant_length=None,
        vowel="pau",
        vowel_length=0,
        pitch=0,
    )


def _generate_accent_phrase(labels: list[_Label], with_pau: bool) -> AccentPhrase:
    """ラベル系列とポーズの有無からアクセント句を生成する。"""
    if len(labels) == 0:
        raise RuntimeError("ラベルが無いためアクセント句を生成できません。")

    moras: list[Mora] = []
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
        moras.append(_generate_mora(consonant=consonant, vowel=vowel))

    if labels[0].accent_position is None:
        msg = "アクセント位置が指定されていません。"
        raise RuntimeError(msg)
    accent = labels[0].accent_position
    # アクセント位置の値がアクセント句内のモーラ数を超える場合はクリップ（ワークアラウンド、VOICEVOX/voicevox_engine#55 を参照）
    accent = accent if accent <= len(moras) else len(moras)

    return AccentPhrase(
        moras=moras,
        accent=accent,
        pause_mora=_generate_pau_mora() if with_pau else None,
        is_interrogative=vowel.is_interrogative,
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


AccentPhaseLabels: TypeAlias = list[_Label]
PauseGroup: TypeAlias = list[AccentPhaseLabels]


def full_context_labels_to_accent_phrases(
    full_context_labels: list[str],
) -> list[AccentPhrase]:
    """フルコンテキストラベルからアクセント句系列を生成する"""
    all_labels = map(_Label.from_feature, full_context_labels)

    pause_group_labels_list = [
        list(labels)
        for is_pau, labels in groupby(all_labels, lambda label: label.is_pause)
        if not is_pau
    ]

    pause_groups: list[PauseGroup] = []
    for pause_group_labels in pause_group_labels_list:
        groups = groupby(
            pause_group_labels,
            lambda label: (label.breath_group_index, label.accent_phrase_index),
        )
        pause_groups.append([list(labels) for _, labels in groups])

    accent_phrases: list[AccentPhrase] = []
    for i_pause_group, pause_group in enumerate(pause_groups):
        is_last_group = i_pause_group == len(pause_groups) - 1

        for i_accent_phrase, labels in enumerate(pause_group):
            is_last_phrase = i_accent_phrase == len(pause_group) - 1
            with_pau = is_last_phrase and not is_last_group
            accent_phrase = _generate_accent_phrase(labels, with_pau=with_pau)
            accent_phrases.append(accent_phrase)

    return accent_phrases
