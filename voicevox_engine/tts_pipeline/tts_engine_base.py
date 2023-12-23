import copy
from abc import ABCMeta, abstractmethod
from typing import List

import numpy as np

from ..model import AccentPhrase, AudioQuery, Mora
from .full_context_label import text_to_accent_phrases
from .mora_list import openjtalk_mora2text

# 疑問文語尾定数
UPSPEAK_LENGTH = 0.15
UPSPEAK_PITCH_ADD = 0.3
UPSPEAK_PITCH_MAX = 6.5


def apply_interrogative_upspeak(
    accent_phrases: list[AccentPhrase], enable_interrogative_upspeak: bool
) -> list[AccentPhrase]:
    """必要に応じて各アクセント句の末尾へ疑問形モーラ（同一母音・継続長 0.15秒・音高↑）を付与する"""
    # NOTE: 将来的にAudioQueryインスタンスを引数にする予定
    if not enable_interrogative_upspeak:
        return accent_phrases

    for accent_phrase in accent_phrases:
        moras = accent_phrase.moras
        if len(moras) == 0:
            continue
        # 疑問形補正条件: 疑問形アクセント句 & 末尾有声モーラ
        if accent_phrase.is_interrogative and moras[-1].pitch > 0:
            last_mora = copy.deepcopy(moras[-1])
            upspeak_mora = Mora(
                text=openjtalk_mora2text[last_mora.vowel],
                consonant=None,
                consonant_length=None,
                vowel=last_mora.vowel,
                vowel_length=UPSPEAK_LENGTH,
                pitch=min(last_mora.pitch + UPSPEAK_PITCH_ADD, UPSPEAK_PITCH_MAX),
            )
            accent_phrase.moras += [upspeak_mora]
    return accent_phrases


class TTSEngineBase(metaclass=ABCMeta):
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
        query.accent_phrases = apply_interrogative_upspeak(
            query.accent_phrases, enable_interrogative_upspeak
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
