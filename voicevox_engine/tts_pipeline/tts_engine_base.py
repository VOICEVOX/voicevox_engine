import copy
from abc import ABCMeta, abstractmethod
from typing import List, Optional

import numpy as np

from ..model import AccentPhrase, AudioQuery, Mora
from . import full_context_label
from .full_context_label import Utterance, extract_full_context_label
from .mora_list import openjtalk_mora2text

# 疑問文語尾定数
UPSPEAK_LENGTH = 0.15
UPSPEAK_PITCH_ADD = 0.3
UPSPEAK_PITCH_MAX = 6.5


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


def adjust_interrogative_accent_phrases(
    accent_phrases: list[AccentPhrase]
) -> list[AccentPhrase]:
    """必要に応じて各アクセント句の末尾へ疑問形モーラ（同一母音・継続長 0.15秒・音高↑）を付与する"""
    for accent_phrase in accent_phrases:
        moras = copy.deepcopy(accent_phrase.moras)
        # 疑問形補正条件: 疑問形フラグON & 終端有声母音
        if accent_phrase.is_interrogative and not (len(moras) == 0 or moras[-1].pitch == 0):
            last_mora = moras[-1]
            interrogative_mora = Mora(
                text=openjtalk_mora2text[last_mora.vowel],
                consonant=None,
                consonant_length=None,
                vowel=last_mora.vowel,
                vowel_length=UPSPEAK_LENGTH,
                pitch=min(last_mora.pitch + UPSPEAK_PITCH_ADD, UPSPEAK_PITCH_MAX),
            )
            moras.append(interrogative_mora)
        accent_phrase.moras = moras
    return accent_phrases


def full_context_label_moras_to_moras(
    full_context_moras: List[full_context_label.Mora],
) -> List[Mora]:
    """
    Moraクラスのキャスト (`full_context_label.Mora` -> `Mora`)
    Parameters
    ----------
    full_context_moras : List[full_context_label.Mora]
        モーラ系列
    Returns
    -------
    moras : List[Mora]
        モーラ系列。音素長・モーラ音高は 0 初期化
    """
    return [
        Mora(
            text=mora_to_text("".join([p.phoneme for p in mora.phonemes])),
            consonant=(mora.consonant.phoneme if mora.consonant is not None else None),
            consonant_length=0 if mora.consonant is not None else None,
            vowel=mora.vowel.phoneme,
            vowel_length=0,
            pitch=0,
        )
        for mora in full_context_moras
    ]


def utterance_to_accent_phrases(utterance: Utterance) -> list[AccentPhrase]:
    """Utteranceインスタンスをアクセント句系列へドメイン変換する"""
    return [
        AccentPhrase(
            moras=full_context_label_moras_to_moras(accent_phrase.moras),
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


def test_to_accent_phrases(text: str) -> list[AccentPhrase]:
    """日本語テキストからアクセント句系列を生成"""
    if len(text.strip()) == 0:
        return []

    # 音素とアクセントの推定
    utterance = extract_full_context_label(text)
    if len(utterance.breath_groups) == 0:
        return []

    return utterance_to_accent_phrases(utterance)


class TTSEngineBase(metaclass=ABCMeta):
    @property
    @abstractmethod
    def default_sampling_rate(self) -> int:
        raise NotImplementedError

    @property
    @abstractmethod
    def speakers(self) -> str:
        """話者情報（json文字列）"""
        # FIXME: jsonではなくModelを返すようにする
        raise NotImplementedError

    @property
    @abstractmethod
    def supported_devices(self) -> Optional[str]:
        """
        デバイス対応情報
        Returns
        -------
            対応デバイス一覧（None: 情報取得不可）
        """
        raise NotImplementedError

    def initialize_style_id_synthesis(  # noqa: B027
        self, style_id: int, skip_reinit: bool
    ):
        """
        指定したスタイルでの音声合成を初期化する。
        何度も実行可能。未実装の場合は何もしない。
        Parameters
        ----------
        style_id : int
            スタイルID
        skip_reinit : bool
            True の場合, 既に初期化済みの話者の再初期化をスキップします
        """
        pass

    def is_initialized_style_id_synthesis(self, style_id: int) -> bool:
        """
        指定したスタイルでの音声合成が初期化されているかどうかを返す
        Parameters
        ----------
        style_id : int
            スタイルID
        Returns
        -------
        bool
            初期化されているかどうか
        """
        return True

    @abstractmethod
    def replace_phoneme_length(
        self, accent_phrases: List[AccentPhrase], style_id: int
    ) -> List[AccentPhrase]:
        """
        音素長の更新
        Parameters
        ----------
        accent_phrases : List[AccentPhrase]
            アクセント句系列
        style_id : int
            スタイルID
        Returns
        -------
        accent_phrases : List[AccentPhrase]
            音素長が更新されたアクセント句系列
        """
        raise NotImplementedError()

    @abstractmethod
    def replace_mora_pitch(
        self, accent_phrases: List[AccentPhrase], style_id: int
    ) -> List[AccentPhrase]:
        """
        モーラ音高の更新
        Parameters
        ----------
        accent_phrases : List[AccentPhrase]
            アクセント句系列
        style_id : int
            スタイルID
        Returns
        -------
        accent_phrases : List[AccentPhrase]
            モーラ音高が更新されたアクセント句系列
        """
        raise NotImplementedError()

    def replace_mora_data(
        self, accent_phrases: List[AccentPhrase], style_id: int
    ) -> List[AccentPhrase]:
        """
        音素長・モーラ音高の更新
        Parameters
        ----------
        accent_phrases : List[AccentPhrase]
            アクセント句系列
        style_id : int
            スタイルID
        Returns
        -------
        accent_phrases : List[AccentPhrase]
            アクセント句系列
        """
        return self.replace_mora_pitch(
            accent_phrases=self.replace_phoneme_length(
                accent_phrases=accent_phrases, style_id=style_id
            ),
            style_id=style_id,
        )

    def create_accent_phrases(self, text: str, style_id: int) -> List[AccentPhrase]:
        """
        テキストからアクセント句系列を生成。
        音素長やモーラ音高も更新。
        Parameters
        ----------
        text : str
            日本語テキスト
        style_id : int
            スタイルID
        Returns
        -------
        accent_phrases : List[AccentPhrase]
            アクセント句系列
        """
        # 音素とアクセントの推定
        accent_phrases = test_to_accent_phrases(text)

        # 音素長・モーラ音高の推定と更新
        accent_phrases = self.replace_mora_data(
            accent_phrases=accent_phrases,
            style_id=style_id,
        )
        return accent_phrases

    def synthesis(
        self,
        query: AudioQuery,
        style_id: int,
        enable_interrogative_upspeak: bool = True,
    ) -> np.ndarray:
        """
        音声合成用のクエリ内の疑問文指定されたMoraを変形した後、
        継承先における実装`_synthesis_impl`を使い音声合成を行う
        Parameters
        ----------
        query : AudioQuery
            音声合成用のクエリ
        style_id : int
            スタイルID
        enable_interrogative_upspeak : bool
            疑問系のテキストの語尾を自動調整する機能を有効にするか
        Returns
        -------
        wave : numpy.ndarray
            音声合成結果
        """
        # モーフィング時などに同一参照のqueryで複数回呼ばれる可能性があるので、元の引数のqueryに破壊的変更を行わない
        query = copy.deepcopy(query)
        if enable_interrogative_upspeak:
            query.accent_phrases = adjust_interrogative_accent_phrases(
                query.accent_phrases
            )
        return self._synthesis_impl(query, style_id)

    @abstractmethod
    def _synthesis_impl(
        self,
        query: AudioQuery,
        style_id: int,
    ) -> np.ndarray:
        """
        音声合成用のクエリから音声合成に必要な情報を構成し、実際に音声合成を行う
        Parameters
        ----------
        query : AudioQuery
            音声合成用のクエリ
        style_id : int
            スタイルID
        Returns
        -------
        wave : numpy.ndarray
            音声合成結果
        """
        raise NotImplementedError()
