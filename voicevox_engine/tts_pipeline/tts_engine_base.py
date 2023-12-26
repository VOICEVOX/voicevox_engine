from abc import ABCMeta, abstractmethod
from typing import List

import numpy as np

from ..model import AccentPhrase, AudioQuery
from .text_analyzer import text_to_accent_phrases


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
        """音声合成用のクエリ・スタイルID・疑問文語尾自動調整フラグに基づいて音声波形を生成する"""
        raise NotImplementedError()
