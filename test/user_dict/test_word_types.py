from unittest import TestCase

from voicevox_engine.dict.part_of_speech_data import part_of_speech_data
from voicevox_engine.model import WordTypes


class TestWordTypes(TestCase):
    def test_word_types(self):
        self.assertCountEqual(list(WordTypes), list(part_of_speech_data.keys()))
