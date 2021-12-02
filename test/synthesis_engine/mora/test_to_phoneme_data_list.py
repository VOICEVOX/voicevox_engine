from unittest import TestCase

from ...data_hello_hiho import str_list_hello_hiho, phoneme_data_list_hello_hiho

from voicevox_engine.synthesis_engine.mora import to_phoneme_data_list

class TestToPhonemeDataList(TestCase):
    def test_to_phoneme_data_list(self):
        phoneme_data_list = to_phoneme_data_list(str_list_hello_hiho)
        self.assertEqual(phoneme_data_list, phoneme_data_list_hello_hiho)
