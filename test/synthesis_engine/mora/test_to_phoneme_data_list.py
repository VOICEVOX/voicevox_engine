from unittest import TestCase

from voicevox_engine.synthesis_engine.mora import to_phoneme_data_list

from ... import data_hello_hiho


class TestToPhonemeDataList(TestCase):
    def test_to_phoneme_data_list(self):
        phoneme_data_list = to_phoneme_data_list(data_hello_hiho.str_list)
        self.assertEqual(phoneme_data_list, data_hello_hiho.phoneme_data_list)
