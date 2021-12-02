from typing import List

from ..acoustic_feature_extractor import OjtPhoneme


def to_phoneme_data_list(phoneme_str_list: List[str]):
    """
    phoneme文字列のリストを、OjtPhonemeクラスのリストに変換する
    Parameters
    ----------
    phoneme_str_list : List[str]
        phoneme文字列のリスト
    Returns
    -------
    phoneme_list : List[OjtPhoneme]
        変換されたOjtPhonemeクラスのリスト
    """
    phoneme_data_list = [
        OjtPhoneme(phoneme=p, start=i, end=i + 1)
        for i, p in enumerate(phoneme_str_list)
    ]
    phoneme_data_list = OjtPhoneme.convert(phoneme_data_list)
    return phoneme_data_list
