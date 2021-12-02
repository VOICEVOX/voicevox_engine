from unittest import TestCase

from copy import deepcopy

from ...data_hello_hiho import accent_phrases_hello_hiho
from voicevox_engine.acoustic_feature_extractor import OjtPhoneme
from voicevox_engine.synthesis_engine.mora import pre_process

class TestPreProcess(TestCase):
    def test_pre_process(self):
        flatten_moras, phoneme_data_list = pre_process(
            deepcopy(accent_phrases_hello_hiho)
        )

        mora_index = 0
        phoneme_index = 1

        self.assertEqual(phoneme_data_list[0], OjtPhoneme("pau", 0, 1))
        for accent_phrase in accent_phrases_hello_hiho:
            moras = accent_phrase.moras
            for mora in moras:
                self.assertEqual(flatten_moras[mora_index], mora)
                mora_index += 1
                if mora.consonant is not None:
                    self.assertEqual(
                        phoneme_data_list[phoneme_index],
                        OjtPhoneme(mora.consonant, phoneme_index, phoneme_index + 1),
                    )
                    phoneme_index += 1
                self.assertEqual(
                    phoneme_data_list[phoneme_index],
                    OjtPhoneme(mora.vowel, phoneme_index, phoneme_index + 1),
                )
                phoneme_index += 1
            if accent_phrase.pause_mora:
                self.assertEqual(flatten_moras[mora_index], accent_phrase.pause_mora)
                mora_index += 1
                self.assertEqual(
                    phoneme_data_list[phoneme_index],
                    OjtPhoneme("pau", phoneme_index, phoneme_index + 1),
                )
                phoneme_index += 1
        self.assertEqual(
            phoneme_data_list[phoneme_index],
            OjtPhoneme("pau", phoneme_index, phoneme_index + 1),
        )
