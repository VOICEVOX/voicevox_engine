import copy
from abc import ABCMeta, abstractmethod
from typing import List

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


def add_interrogative_mora_if_last_phoneme_is_interrogative(
    full_context_accent_phrase: full_context_label.AccentPhrase,
    enable_interrogative: bool,
) -> List[full_context_label.Mora]:
    """
    enable_interrogativeが有効になっていて与えられたfull_context_accent_phraseが疑問系だった場合、
    accent_phraseのmoraに対して疑問系の発音を擬似的に行うMoraを末尾に一つ追加する
    """
    last_mora = full_context_accent_phrase.moras[-1]
    return (
        full_context_accent_phrase.moras
        + [full_context_label.Mora(None, last_mora.vowel)]
        if full_context_accent_phrase.is_interrogative and enable_interrogative
        else full_context_accent_phrase.moras
    )


def adjust_interrogative_accent_phrases(
    accent_phrases: List[AccentPhrase],
    fcl_accent_phrases: List[full_context_label.AccentPhrase],
    enable_interrogative: bool,
) -> List[AccentPhrase]:
    """
    enable_interrogativeが有効になっていて与えられたaccent_phrasesに疑問系のものがあった場合、
    SynthesisEngineの実装によって調整されたあとの各accent_phraseの末尾にある疑問系発音用のMoraに対して直前のMoraより少し音を高くすることで疑問文ぽくする
    """
    return [
        AccentPhrase(
            moras=adjust_interrogative_moras(accent_phrase.moras)
            if enable_interrogative and fcl_accent_phrase.is_interrogative
            else accent_phrase.moras,
            accent=accent_phrase.accent,
            pause_mora=accent_phrase.pause_mora,
        )
        for accent_phrase, fcl_accent_phrase in zip(accent_phrases, fcl_accent_phrases)
    ]


def adjust_interrogative_moras(moras: List[Mora]) -> List[Mora]:
    if len(moras) <= 1:
        return moras
    moras = copy.deepcopy(moras)
    moras[-1] = adjust_interrogative_mora(moras[-1], moras[-2])
    return moras


def adjust_interrogative_mora(mora: Mora, before_mora: Mora) -> Mora:
    mora = copy.deepcopy(mora)
    fix_vowel_length = 0.15
    mora.vowel_length = fix_vowel_length

    adjust_pitch = 0.3
    max_pitch = 6.5
    mora.pitch = min(before_mora.pitch + adjust_pitch, max_pitch)
    return mora


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
    @abstractmethod
    def replace_phoneme_length(
        self, accent_phrases: List[AccentPhrase], speaker_id: int
    ) -> List[AccentPhrase]:
        """
        accent_phrasesの母音・子音の長さを設定する
        Parameters
        ----------
        accent_phrases : List[AccentPhrase]
            アクセント句モデルのリスト
        speaker_id : int
            話者ID
        Returns
        -------
        accent_phrases : List[AccentPhrase]
            母音・子音の長さが設定されたアクセント句モデルのリスト
        """
        raise NotImplementedError()

    @abstractmethod
    def replace_mora_pitch(
        self, accent_phrases: List[AccentPhrase], speaker_id: int
    ) -> List[AccentPhrase]:
        """
        accent_phrasesの音高(ピッチ)を設定する
        Parameters
        ----------
        accent_phrases : List[AccentPhrase]
            アクセント句モデルのリスト
        speaker_id : int
            話者ID
        Returns
        -------
        accent_phrases : List[AccentPhrase]
            音高(ピッチ)が設定されたアクセント句モデルのリスト
        """
        raise NotImplementedError()

    def replace_mora_data(
        self,
        accent_phrases: List[AccentPhrase],
        fcl_accent_phrases: List[full_context_label.AccentPhrase],
        enable_interrogative: bool,
        speaker_id: int,
    ) -> List[AccentPhrase]:
        return adjust_interrogative_accent_phrases(
            accent_phrases=self.replace_mora_pitch(
                accent_phrases=self.replace_phoneme_length(
                    accent_phrases=accent_phrases,
                    speaker_id=speaker_id,
                ),
                speaker_id=speaker_id,
            ),
            fcl_accent_phrases=fcl_accent_phrases,
            enable_interrogative=enable_interrogative,
        )

    def create_accent_phrases(
        self, text: str, speaker_id: int, enable_interrogative: bool
    ) -> List[AccentPhrase]:
        if len(text.strip()) == 0:
            return []

        utterance = extract_full_context_label(text)
        if len(utterance.breath_groups) == 0:
            return []

        fcl_accent_phrases = [
            accent_phrase
            for breath_group in utterance.breath_groups
            for accent_phrase in breath_group.accent_phrases
        ]

        return self.replace_mora_data(
            accent_phrases=[
                AccentPhrase(
                    moras=full_context_label_moras_to_moras(
                        add_interrogative_mora_if_last_phoneme_is_interrogative(
                            accent_phrase,
                            enable_interrogative,
                        ),
                    ),
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
                )
                for i_breath_group, breath_group in enumerate(utterance.breath_groups)
                for i_accent_phrase, accent_phrase in enumerate(
                    breath_group.accent_phrases
                )
            ],
            fcl_accent_phrases=fcl_accent_phrases,
            enable_interrogative=enable_interrogative,
            speaker_id=speaker_id,
        )

    @abstractmethod
    def synthesis(self, query: AudioQuery, speaker_id: int):
        """
        音声合成クエリから音声合成に必要な情報を構成し、実際に音声合成を行う
        Parameters
        ----------
        query : AudioQuery
            音声合成クエリ
        speaker_id : int
            話者ID
        Returns
        -------
        wave : numpy.ndarray
            音声合成結果
        """
        raise NotImplementedError()
