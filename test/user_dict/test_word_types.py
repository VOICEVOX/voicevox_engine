from unittest import TestCase

from voicevox_engine.model import WordTypes
from voicevox_engine.user_dict.part_of_speech_data import part_of_speech_data


class TestWordTypes(TestCase):
    def test_word_types(self) -> None:
        self.assertCountEqual(list(WordTypes), list(part_of_speech_data.keys()))
