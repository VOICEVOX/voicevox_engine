from unittest import TestCase

from voicevox_engine.model import WordTypes
from voicevox_engine.user_dict.part_of_speech_data import part_of_speech_data


def test_word_types() -> None:
    word_types = list(WordTypes)
    part_of_speeches = list(part_of_speech_data.keys())
    assert sorted(word_types) == sorted(part_of_speeches)
