
from typing import List
from itertools import chain
from ..model import AccentPhrase, Mora


def to_flatten_moras(accent_phrases: List[AccentPhrase]) -> List[Mora]:
    """
    accent_phrasesに含まれるMora(とpause_moraがあればそれも)を
    すべて一つのリストに結合する
    Parameters
    ----------
    accent_phrases : List[AccentPhrase]
        AccentPhraseのリスト
    Returns
    -------
    moras : List[Mora]
        結合されたMoraのリストを返す
    """
    return list(
        chain.from_iterable(
            accent_phrase.moras
            + (
                [accent_phrase.pause_mora]
                if accent_phrase.pause_mora is not None
                else []
            )
            for accent_phrase in accent_phrases
        )
    )
