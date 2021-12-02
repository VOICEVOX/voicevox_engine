import sys
from itertools import chain
from typing import List, Tuple

from ..acoustic_feature_extractor import OjtPhoneme
from ..model import AccentPhrase, Mora

from .to_flatten_moras import to_flatten_moras
from .to_phoneme_data_list import to_phoneme_data_list


def pre_process(
    accent_phrases: List[AccentPhrase],
) -> Tuple[List[Mora], List[OjtPhoneme]]:
    """
    AccentPhraseモデルのリストを整形し、処理に必要なデータの原型を作り出す
    Parameters
    ----------
    accent_phrases : List[AccentPhrase]
        AccentPhraseモデルのリスト
    Returns
    -------
    flatten_moras : List[Mora]
        AccentPhraseモデルのリスト内に含まれるすべてのMoraをリスト化したものを返す
    phoneme_data_list : List[OjtPhoneme]
        flatten_morasから取り出したすべてのPhonemeをOjtPhonemeに変換したものを返す
    """
    flatten_moras = to_flatten_moras(accent_phrases)

    phoneme_each_mora = [
        ([mora.consonant] if mora.consonant is not None else []) + [mora.vowel]
        for mora in flatten_moras
    ]
    phoneme_str_list = list(chain.from_iterable(phoneme_each_mora))
    phoneme_str_list = ["pau"] + phoneme_str_list + ["pau"]

    phoneme_data_list = to_phoneme_data_list(phoneme_str_list)

    return flatten_moras, phoneme_data_list
