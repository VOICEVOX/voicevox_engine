import copy
from abc import ABCMeta, abstractmethod
from typing import List, Optional

import numpy as np

from ..model import AccentPhrase, AudioQuery, Mora
from .full_context_label import text_to_accent_phrases
from .mora_list import openjtalk_mora2text


def adjust_interrogative_accent_phrases(
    accent_phrases: List[AccentPhrase],
) -> List[AccentPhrase]:
    """
    アクセント句系列の必要に応じて疑問系に補正
    各accent_phraseの末尾のモーラより少し音の高い有声母音モーラを付与するすることで疑問文ぽくする
    Parameters
    ----------
    accent_phrases : List[AccentPhrase]
        アクセント句系列
    Returns
    -------
    accent_phrases : List[AccentPhrase]
        必要に応じて疑問形補正されたアクセント句系列
    """
    # NOTE: リファクタリング時に適切な場所へ移動させること
    return [
        AccentPhrase(
            moras=adjust_interrogative_moras(accent_phrase),
            accent=accent_phrase.accent,
            pause_mora=accent_phrase.pause_mora,
            is_interrogative=accent_phrase.is_interrogative,
        )
        for accent_phrase in accent_phrases
    ]


def adjust_interrogative_moras(accent_phrase: AccentPhrase) -> List[Mora]:
    """
    アクセント句に含まれるモーラ系列の必要に応じた疑問形補正
    Parameters
    ----------
    accent_phrase : AccentPhrase
        アクセント句
    Returns
    -------
    moras : List[Mora]
        補正済みモーラ系列
    """
    moras = copy.deepcopy(accent_phrase.moras)
    # 疑問形補正条件: 疑問形フラグON & 終端有声母音
    if accent_phrase.is_interrogative and not (len(moras) == 0 or moras[-1].pitch == 0):
        interrogative_mora = make_interrogative_mora(moras[-1])
        moras.append(interrogative_mora)
        return moras
    else:
        return moras


def make_interrogative_mora(last_mora: Mora) -> Mora:
    """
    疑問形用のモーラ（同一母音・継続長 0.15秒・音高↑）の生成
    Parameters
    ----------
    last_mora : Mora
        疑問形にするモーラ
    Returns
    -------
    mora : Mora
        疑問形用のモーラ
    """
    fix_vowel_length = 0.15
    adjust_pitch = 0.3
    max_pitch = 6.5
    return Mora(
        text=openjtalk_mora2text[last_mora.vowel],
        consonant=None,
        consonant_length=None,
        vowel=last_mora.vowel,
        vowel_length=fix_vowel_length,
        pitch=min(last_mora.pitch + adjust_pitch, max_pitch),
    )


class SynthesisEngineBase(metaclass=ABCMeta):
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
        accent_phrases = text_to_accent_phrases(text)

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
