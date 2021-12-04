from unittest import TestCase

from voicevox_engine.acoustic_feature_extractor import OjtPhoneme
from voicevox_engine.synthesis_engine.mora import split_mora

from ... import data_hello_hiho


class TestSplitMora(TestCase):
    def test_split_mora(self):
        consonant_phoneme_list, vowel_phoneme_list, vowel_indexes = split_mora(
            data_hello_hiho.phoneme_data_list
        )

        self.assertEqual(vowel_indexes, [0, 2, 3, 5, 7, 9, 10, 12, 14, 16, 18, 19])
        self.assertEqual(
            vowel_phoneme_list,
            [
                OjtPhoneme(phoneme="pau", start=0, end=1),
                OjtPhoneme(phoneme="o", start=2, end=3),
                OjtPhoneme(phoneme="N", start=3, end=4),
                OjtPhoneme(phoneme="i", start=5, end=6),
                OjtPhoneme(phoneme="i", start=7, end=8),
                OjtPhoneme(phoneme="a", start=9, end=10),
                OjtPhoneme(phoneme="pau", start=10, end=11),
                OjtPhoneme(phoneme="i", start=12, end=13),
                OjtPhoneme(phoneme="o", start=14, end=15),
                OjtPhoneme(phoneme="e", start=16, end=17),
                OjtPhoneme(phoneme="U", start=18, end=19),
                OjtPhoneme(phoneme="pau", start=19, end=20),
            ],
        )
        self.assertEqual(
            consonant_phoneme_list,
            [
                None,
                OjtPhoneme(phoneme="k", start=1, end=2),
                None,
                OjtPhoneme(phoneme="n", start=4, end=5),
                OjtPhoneme(phoneme="ch", start=6, end=7),
                OjtPhoneme(phoneme="w", start=8, end=9),
                None,
                OjtPhoneme(phoneme="h", start=11, end=12),
                OjtPhoneme(phoneme="h", start=13, end=14),
                OjtPhoneme(phoneme="d", start=15, end=16),
                OjtPhoneme(phoneme="s", start=17, end=18),
                None,
            ],
        )
