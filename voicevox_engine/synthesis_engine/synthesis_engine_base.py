import copy
from abc import ABCMeta, abstractmethod
from typing import List, Optional

import numpy as np

from .. import full_context_label
from ..full_context_label import extract_full_context_label
from ..model import AccentPhrase, AudioQuery, Mora
from ..mora_list import openjtalk_mora2text


def mora_to_text(mora: str) -> str:
    if mora[-1:] in ["A", "I", "U", "E", "O"]:
        # 無声化母音を小文字に
        mora = mora[:-1] + mora[-1].lower()
    if mora in openjtalk_mora2text:
        return openjtalk_mora2text[mora]
    else:
        return mora


def adjust_interrogative_accent_phrases(
    accent_phrases: List[AccentPhrase],
) -> List[AccentPhrase]:
    """
    enable_interrogative_upspeakが有効になっていて与えられたaccent_phrasesに疑問系のものがあった場合、
    各accent_phraseの末尾にある疑問系発音用のMoraに対して直前のMoraより少し音を高くすることで疑問文ぽくする
    NOTE: リファクタリング時に適切な場所へ移動させること
    """
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
    moras = copy.deepcopy(accent_phrase.moras)
    if accent_phrase.is_interrogative and not (len(moras) == 0 or moras[-1].pitch == 0):
        interrogative_mora = make_interrogative_mora(moras[-1])
        moras.append(interrogative_mora)
        return moras
    else:
        return moras


def make_interrogative_mora(last_mora: Mora) -> Mora:
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


def full_context_label_moras_to_moras(
    full_context_moras: List[full_context_label.Mora],
) -> List[Mora]:
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


class SynthesisEngineBase(metaclass=ABCMeta):
    # FIXME: jsonではなくModelを返すようにする
    @property
    @abstractmethod
    def speakers(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def supported_devices(self) -> Optional[str]:
        raise NotImplementedError

    def initialize_style_id_synthesis(  # noqa: B027
        self,
        style_id: int,
        skip_reinit: bool,
    ):
        """
        指定したスタイルでの音声合成を初期化する。何度も実行可能。
        未実装の場合は何もしない
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
        accent_phrasesの母音・子音の長さを設定する
        Parameters
        ----------
        accent_phrases : List[AccentPhrase]
            アクセント句モデルのリスト
        style_id : int
            スタイルID
        Returns
        -------
        accent_phrases : List[AccentPhrase]
            母音・子音の長さが設定されたアクセント句モデルのリスト
        """
        raise NotImplementedError()

    @abstractmethod
    def replace_mora_pitch(
        self,
        accent_phrases: List[AccentPhrase],
        style_id: int,
    ) -> List[AccentPhrase]:
        """
        accent_phrasesの音高(ピッチ)を設定する
        Parameters
        ----------
        accent_phrases : List[AccentPhrase]
            アクセント句モデルのリスト
        style_id : int
            スタイルID
        Returns
        -------
        accent_phrases : List[AccentPhrase]
            音高(ピッチ)が設定されたアクセント句モデルのリスト
        """
        raise NotImplementedError()

    def replace_mora_data(
        self,
        accent_phrases: List[AccentPhrase],
        style_id: int,
    ) -> List[AccentPhrase]:
        return self.replace_mora_pitch(
            accent_phrases=self.replace_phoneme_length(
                accent_phrases=accent_phrases,
                style_id=style_id,
            ),
            style_id=style_id,
        )

    def create_accent_phrases(self, text: str, style_id: int) -> List[AccentPhrase]:
        if len(text.strip()) == 0:
            return []

        utterance = extract_full_context_label(text)
        if len(utterance.breath_groups) == 0:
            return []

        accent_phrases = self.replace_mora_data(
            accent_phrases=[
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
                for i_accent_phrase, accent_phrase in enumerate(
                    breath_group.accent_phrases
                )
            ],
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
        音声合成クエリ内の疑問文指定されたMoraを変形した後、
        継承先における実装`_synthesis_impl`を使い音声合成を行う
        Parameters
        ----------
        query : AudioQuery
            音声合成クエリ
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
        音声合成クエリから音声合成に必要な情報を構成し、実際に音声合成を行う
        Parameters
        ----------
        query : AudioQuery
            音声合成クエリ
        style_id : int
            スタイルID
        Returns
        -------
        wave : numpy.ndarray
            音声合成結果
        """
        raise NotImplementedError()
