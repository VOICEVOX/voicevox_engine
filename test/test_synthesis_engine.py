from copy import deepcopy
from unittest import TestCase
from unittest.mock import Mock

import numpy

from voicevox_engine.acoustic_feature_extractor import OjtPhoneme
from voicevox_engine.model import AccentPhrase, Mora
from voicevox_engine.synthesis_engine import (
    SynthesisEngine,
    split_mora,
    to_flatten_moras,
    to_phoneme_data_list,
)


def yukarin_s_mock(length: int, phoneme_list: numpy.ndarray, speaker_id: numpy.ndarray):
    result = []
    # mockとしての適当な処理、特に意味はない
    for i in range(length):
        result.append(float(phoneme_list[i] * 0.5 + speaker_id))
    return numpy.array(result)


def yukarin_sa_mock(
    length: int,
    vowel_phoneme_list: numpy.ndarray,
    consonant_phoneme_list: numpy.ndarray,
    start_accent_list: numpy.ndarray,
    end_accent_list: numpy.ndarray,
    start_accent_phrase_list: numpy.ndarray,
    end_accent_phrase_list: numpy.ndarray,
    speaker_id: numpy.ndarray,
):
    result = []
    # mockとしての適当な処理、特に意味はない
    for i in range(length):
        result.append(
            float(
                (
                    vowel_phoneme_list[0][i]
                    + consonant_phoneme_list[0][i]
                    + start_accent_list[0][i]
                    + end_accent_list[0][i]
                    + start_accent_phrase_list[0][i]
                    + end_accent_phrase_list[0][i]
                )
                * 0.5
                + speaker_id
            )
        )
    return numpy.array(result)[numpy.newaxis]


class TestSynthesisEngine(TestCase):
    def setUp(self):
        super().setUp()
        self.str_list_hello_hiho = (
            "sil k o N n i ch i w a pau h i h o d e s U sil".split()
        )
        self.phoneme_data_list_hello_hiho = [
            OjtPhoneme(phoneme=p, start=i, end=i + 1)
            for i, p in enumerate(
                "pau k o N n i ch i w a pau h i h o d e s U pau".split()
            )
        ]
        self.accent_phrases_hello_hiho = [
            AccentPhrase(
                moras=[
                    Mora(
                        text="コ",
                        consonant="k",
                        consonant_length=0.0,
                        vowel="o",
                        vowel_length=0.0,
                        pitch=0.0,
                    ),
                    Mora(
                        text="ン",
                        consonant=None,
                        consonant_length=None,
                        vowel="N",
                        vowel_length=0.0,
                        pitch=0.0,
                    ),
                    Mora(
                        text="ニ",
                        consonant="n",
                        consonant_length=0.0,
                        vowel="i",
                        vowel_length=0.0,
                        pitch=0.0,
                    ),
                    Mora(
                        text="チ",
                        consonant="ch",
                        consonant_length=0.0,
                        vowel="i",
                        vowel_length=0.0,
                        pitch=0.0,
                    ),
                    Mora(
                        text="ワ",
                        consonant="w",
                        consonant_length=0.0,
                        vowel="a",
                        vowel_length=0.0,
                        pitch=0.0,
                    ),
                ],
                accent=5,
                pause_mora=Mora(
                    text="、",
                    consonant=None,
                    consonant_length=None,
                    vowel="pau",
                    vowel_length=0.0,
                    pitch=0.0,
                ),
            ),
            AccentPhrase(
                moras=[
                    Mora(
                        text="ヒ",
                        consonant="h",
                        consonant_length=0.0,
                        vowel="i",
                        vowel_length=0.0,
                        pitch=0.0,
                    ),
                    Mora(
                        text="ホ",
                        consonant="h",
                        consonant_length=0.0,
                        vowel="o",
                        vowel_length=0.0,
                        pitch=0.0,
                    ),
                    Mora(
                        text="デ",
                        consonant="d",
                        consonant_length=0.0,
                        vowel="e",
                        vowel_length=0.0,
                        pitch=0.0,
                    ),
                    Mora(
                        text="ス",
                        consonant="s",
                        consonant_length=0.0,
                        vowel="U",
                        vowel_length=0.0,
                        pitch=0.0,
                    ),
                ],
                accent=1,
                pause_mora=None,
            ),
        ]
        self.yukarin_s_mock = Mock(side_effect=yukarin_s_mock)
        self.yukarin_sa_mock = Mock(side_effect=yukarin_sa_mock)
        self.decode_mock = Mock()
        self.synthesis_engine = SynthesisEngine(
            yukarin_s_forwarder=self.yukarin_s_mock,
            yukarin_sa_forwarder=self.yukarin_sa_mock,
            decode_forwarder=self.decode_mock,
            speakers="",
        )

    def test_to_flatten_moras(self):
        flatten_moras = to_flatten_moras(self.accent_phrases_hello_hiho)
        self.assertEqual(
            flatten_moras,
            self.accent_phrases_hello_hiho[0].moras
            + [self.accent_phrases_hello_hiho[0].pause_mora]
            + self.accent_phrases_hello_hiho[1].moras,
        )

    def test_to_phoneme_data_list(self):
        phoneme_data_list = to_phoneme_data_list(self.str_list_hello_hiho)
        self.assertEqual(phoneme_data_list, self.phoneme_data_list_hello_hiho)

    def test_split_mora(self):
        consonant_phoneme_list, vowel_phoneme_list, vowel_indexes = split_mora(
            self.phoneme_data_list_hello_hiho
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

    def test_replace_phoneme_length(self):
        result = self.synthesis_engine.replace_phoneme_length(
            accent_phrases=deepcopy(self.accent_phrases_hello_hiho), speaker_id=1
        )

        # yukarin_sに渡される値の検証
        yukarin_s_args = self.yukarin_s_mock.call_args[1]
        list_length = yukarin_s_args["length"]
        phoneme_list = yukarin_s_args["phoneme_list"]
        self.assertEqual(list_length, 20)
        self.assertEqual(list_length, len(phoneme_list))
        numpy.testing.assert_array_equal(
            phoneme_list,
            numpy.array(
                [
                    0,
                    23,
                    30,
                    4,
                    28,
                    21,
                    10,
                    21,
                    42,
                    7,
                    0,
                    19,
                    21,
                    19,
                    30,
                    12,
                    14,
                    35,
                    6,
                    0,
                ],
                dtype=numpy.int64,
            ),
        )
        self.assertEqual(yukarin_s_args["speaker_id"], 1)

        # flatten_morasを使わずに愚直にaccent_phrasesにデータを反映させてみる
        true_result = deepcopy(self.accent_phrases_hello_hiho)
        index = 1

        def result_value(i: int):
            return float(phoneme_list[i] * 0.5 + 1)

        for accent_phrase in true_result:
            moras = accent_phrase.moras
            for mora in moras:
                if mora.consonant is not None:
                    mora.consonant_length = result_value(index)
                    index += 1
                mora.vowel_length = result_value(index)
                index += 1
            if accent_phrase.pause_mora is not None:
                accent_phrase.pause_mora.vowel_length = result_value(index)
                index += 1

        self.assertEqual(result, true_result)

    def test_replace_mora_pitch(self):
        result = self.synthesis_engine.replace_mora_pitch(
            accent_phrases=deepcopy(self.accent_phrases_hello_hiho), speaker_id=1
        )

        # yukarin_saに渡される値の検証
        yukarin_sa_args = self.yukarin_sa_mock.call_args[1]
        list_length = yukarin_sa_args["length"]
        vowel_phoneme_list = yukarin_sa_args["vowel_phoneme_list"][0]
        consonant_phoneme_list = yukarin_sa_args["consonant_phoneme_list"][0]
        start_accent_list = yukarin_sa_args["start_accent_list"][0]
        end_accent_list = yukarin_sa_args["end_accent_list"][0]
        start_accent_phrase_list = yukarin_sa_args["start_accent_phrase_list"][0]
        end_accent_phrase_list = yukarin_sa_args["end_accent_phrase_list"][0]
        self.assertEqual(list_length, 12)
        self.assertEqual(list_length, len(vowel_phoneme_list))
        self.assertEqual(list_length, len(consonant_phoneme_list))
        self.assertEqual(list_length, len(start_accent_list))
        self.assertEqual(list_length, len(end_accent_list))
        self.assertEqual(list_length, len(start_accent_phrase_list))
        self.assertEqual(list_length, len(end_accent_phrase_list))
        self.assertEqual(yukarin_sa_args["speaker_id"], 1)

        numpy.testing.assert_array_equal(
            vowel_phoneme_list,
            numpy.array(
                [
                    0,
                    30,
                    4,
                    21,
                    21,
                    7,
                    0,
                    21,
                    30,
                    14,
                    6,
                    0,
                ]
            ),
        )
        numpy.testing.assert_array_equal(
            consonant_phoneme_list,
            numpy.array(
                [
                    -1,
                    23,
                    -1,
                    28,
                    10,
                    42,
                    -1,
                    19,
                    19,
                    12,
                    35,
                    -1,
                ]
            ),
        )
        numpy.testing.assert_array_equal(
            start_accent_list, numpy.array([0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0])
        )
        numpy.testing.assert_array_equal(
            end_accent_list, numpy.array([0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0])
        )
        numpy.testing.assert_array_equal(
            start_accent_phrase_list, numpy.array([0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0])
        )
        numpy.testing.assert_array_equal(
            end_accent_phrase_list, numpy.array([0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0])
        )

        # flatten_morasを使わずに愚直にaccent_phrasesにデータを反映させてみる
        true_result = deepcopy(self.accent_phrases_hello_hiho)
        index = 1

        def result_value(i: int):
            # unvoiced_mora_phoneme_listのPhoneme ID版
            unvoiced_mora_phoneme_id_list = [0, 1, 2, 3, 5, 6, 11]
            if vowel_phoneme_list[i] in unvoiced_mora_phoneme_id_list:
                return 0
            return (
                vowel_phoneme_list[i]
                + consonant_phoneme_list[i]
                + start_accent_list[i]
                + end_accent_list[i]
                + start_accent_phrase_list[i]
                + end_accent_phrase_list[i]
            ) * 0.5 + 1

        for accent_phrase in true_result:
            moras = accent_phrase.moras
            for mora in moras:
                mora.pitch = result_value(index)
                index += 1
            if accent_phrase.pause_mora is not None:
                accent_phrase.pause_mora.pitch = result_value(index)
                index += 1

        self.assertEqual(result, true_result)
