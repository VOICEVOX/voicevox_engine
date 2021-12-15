from typing import List, Union
from unittest import TestCase
from unittest.mock import Mock

import numpy

from voicevox_engine.model import AccentPhrase, Mora
from voicevox_engine.synthesis_engine import SynthesisEngine


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


def decode_mock(
    length: int,
    phoneme_size: int,
    f0: numpy.ndarray,
    phoneme: numpy.ndarray,
    speaker_id: Union[numpy.ndarray, int],
):
    result = []
    # mockとしての適当な処理、特に意味はない
    for i in range(length):
        # decode forwardはデータサイズがlengthの256倍になるのでとりあえず256回データをresultに入れる
        for _ in range(256):
            result.append(
                float(
                    f0[i][0] * (numpy.where(phoneme[i] == 1)[0] / phoneme_size)
                    + speaker_id
                )
            )
    return numpy.array(result)


class TestSynthesisEngineBase(TestCase):
    def setUp(self):
        super().setUp()
        self.yukarin_s_mock = Mock(side_effect=yukarin_s_mock)
        self.yukarin_sa_mock = Mock(side_effect=yukarin_sa_mock)
        self.decode_mock = Mock(side_effect=decode_mock)
        self.synthesis_engine = SynthesisEngine(
            yukarin_s_forwarder=self.yukarin_s_mock,
            yukarin_sa_forwarder=self.yukarin_sa_mock,
            decode_forwarder=self.decode_mock,
            speakers="",
        )

    def create_accent_phrases_test_base(
        self, text: str, expected: List[AccentPhrase], enable_interrogative: bool
    ):
        actual = self.synthesis_engine.create_accent_phrases(
            text, 1, enable_interrogative
        )
        self.assertEqual(
            expected,
            actual,
            "case(text:"
            + text
            + ",enable_interrogative:"
            + str(enable_interrogative)
            + ")",
        )

    def test_create_accent_phrases(self):
        self.create_accent_phrases_test_base(
            text="これはありますか？",
            expected=[
                AccentPhrase(
                    moras=[
                        Mora(
                            text="コ",
                            consonant="k",
                            consonant_length=12.5,
                            vowel="o",
                            vowel_length=16.0,
                            pitch=28.0,
                        ),
                        Mora(
                            text="レ",
                            consonant="r",
                            consonant_length=17.5,
                            vowel="e",
                            vowel_length=8.0,
                            pitch=25.0,
                        ),
                        Mora(
                            text="ワ",
                            consonant="w",
                            consonant_length=22.0,
                            vowel="a",
                            vowel_length=4.5,
                            pitch=26.5,
                        ),
                    ],
                    accent=3,
                    pause_mora=None,
                ),
                AccentPhrase(
                    moras=[
                        Mora(
                            text="ア",
                            consonant=None,
                            consonant_length=None,
                            vowel="a",
                            vowel_length=4.5,
                            pitch=4.5,
                        ),
                        Mora(
                            text="リ",
                            consonant="r",
                            consonant_length=17.5,
                            vowel="i",
                            vowel_length=11.5,
                            pitch=28.5,
                        ),
                        Mora(
                            text="マ",
                            consonant="m",
                            consonant_length=14.0,
                            vowel="a",
                            vowel_length=4.5,
                            pitch=18.0,
                        ),
                        Mora(
                            text="ス",
                            consonant="s",
                            consonant_length=18.5,
                            vowel="U",
                            vowel_length=4.0,
                            pitch=0.0,
                        ),
                        Mora(
                            text="カ",
                            consonant="k",
                            consonant_length=12.5,
                            vowel="a",
                            vowel_length=4.5,
                            pitch=16.0,
                        ),
                        Mora(
                            text="ア",
                            consonant=None,
                            consonant_length=None,
                            vowel="a",
                            vowel_length=0.15,
                            pitch=6.5,
                        ),
                    ],
                    accent=3,
                    pause_mora=None,
                ),
            ],
            enable_interrogative=True,
        )

        self.create_accent_phrases_test_base(
            text="これはありますか？",
            expected=[
                AccentPhrase(
                    moras=[
                        Mora(
                            text="コ",
                            consonant="k",
                            consonant_length=12.5,
                            vowel="o",
                            vowel_length=16.0,
                            pitch=28.0,
                        ),
                        Mora(
                            text="レ",
                            consonant="r",
                            consonant_length=17.5,
                            vowel="e",
                            vowel_length=8.0,
                            pitch=25.0,
                        ),
                        Mora(
                            text="ワ",
                            consonant="w",
                            consonant_length=22.0,
                            vowel="a",
                            vowel_length=4.5,
                            pitch=26.5,
                        ),
                    ],
                    accent=3,
                    pause_mora=None,
                ),
                AccentPhrase(
                    moras=[
                        Mora(
                            text="ア",
                            consonant=None,
                            consonant_length=None,
                            vowel="a",
                            vowel_length=4.5,
                            pitch=4.5,
                        ),
                        Mora(
                            text="リ",
                            consonant="r",
                            consonant_length=17.5,
                            vowel="i",
                            vowel_length=11.5,
                            pitch=28.5,
                        ),
                        Mora(
                            text="マ",
                            consonant="m",
                            consonant_length=14.0,
                            vowel="a",
                            vowel_length=4.5,
                            pitch=18.0,
                        ),
                        Mora(
                            text="ス",
                            consonant="s",
                            consonant_length=18.5,
                            vowel="U",
                            vowel_length=4.0,
                            pitch=0.0,
                        ),
                        Mora(
                            text="カ",
                            consonant="k",
                            consonant_length=12.5,
                            vowel="a",
                            vowel_length=4.5,
                            pitch=16.5,
                        ),
                    ],
                    accent=3,
                    pause_mora=None,
                ),
            ],
            enable_interrogative=False,
        )

        self.create_accent_phrases_test_base(
            text="これはありますか",
            expected=[
                AccentPhrase(
                    moras=[
                        Mora(
                            text="コ",
                            consonant="k",
                            consonant_length=12.5,
                            vowel="o",
                            vowel_length=16.0,
                            pitch=28.0,
                        ),
                        Mora(
                            text="レ",
                            consonant="r",
                            consonant_length=17.5,
                            vowel="e",
                            vowel_length=8.0,
                            pitch=25.0,
                        ),
                        Mora(
                            text="ワ",
                            consonant="w",
                            consonant_length=22.0,
                            vowel="a",
                            vowel_length=4.5,
                            pitch=26.5,
                        ),
                    ],
                    accent=3,
                    pause_mora=None,
                ),
                AccentPhrase(
                    moras=[
                        Mora(
                            text="ア",
                            consonant=None,
                            consonant_length=None,
                            vowel="a",
                            vowel_length=4.5,
                            pitch=4.5,
                        ),
                        Mora(
                            text="リ",
                            consonant="r",
                            consonant_length=17.5,
                            vowel="i",
                            vowel_length=11.5,
                            pitch=28.5,
                        ),
                        Mora(
                            text="マ",
                            consonant="m",
                            consonant_length=14.0,
                            vowel="a",
                            vowel_length=4.5,
                            pitch=18.0,
                        ),
                        Mora(
                            text="ス",
                            consonant="s",
                            consonant_length=18.5,
                            vowel="U",
                            vowel_length=4.0,
                            pitch=0.0,
                        ),
                        Mora(
                            text="カ",
                            consonant="k",
                            consonant_length=12.5,
                            vowel="a",
                            vowel_length=4.5,
                            pitch=16.5,
                        ),
                    ],
                    accent=3,
                    pause_mora=None,
                ),
            ],
            enable_interrogative=True,
        )

        self.create_accent_phrases_test_base(
            text="ん",
            expected=[
                AccentPhrase(
                    moras=[
                        Mora(
                            text="ン",
                            consonant=None,
                            consonant_length=None,
                            vowel="N",
                            vowel_length=3.0,
                            pitch=4.5,
                        ),
                    ],
                    accent=1,
                    pause_mora=None,
                )
            ],
            enable_interrogative=True,
        )

        self.create_accent_phrases_test_base(
            text="ん？",
            expected=[
                AccentPhrase(
                    moras=[
                        Mora(
                            text="ン",
                            consonant=None,
                            consonant_length=None,
                            vowel="N",
                            vowel_length=3.0,
                            pitch=4.0,
                        ),
                        Mora(
                            text="ン",
                            consonant=None,
                            consonant_length=None,
                            vowel="N",
                            vowel_length=0.15,
                            pitch=4.3,
                        ),
                    ],
                    accent=1,
                    pause_mora=None,
                )
            ],
            enable_interrogative=True,
        )

        self.create_accent_phrases_test_base(
            text="ん？",
            expected=[
                AccentPhrase(
                    moras=[
                        Mora(
                            text="ン",
                            consonant=None,
                            consonant_length=None,
                            vowel="N",
                            vowel_length=3.0,
                            pitch=4.5,
                        ),
                    ],
                    accent=1,
                    pause_mora=None,
                )
            ],
            enable_interrogative=False,
        )

        self.create_accent_phrases_test_base(
            text="っ",
            expected=[
                AccentPhrase(
                    moras=[
                        Mora(
                            text="ッ",
                            consonant=None,
                            consonant_length=None,
                            vowel="cl",
                            vowel_length=6.5,
                            pitch=0.0,
                        ),
                    ],
                    accent=1,
                    pause_mora=None,
                )
            ],
            enable_interrogative=True,
        )

        self.create_accent_phrases_test_base(
            text="っ？",
            expected=[
                AccentPhrase(
                    moras=[
                        Mora(
                            text="ッ",
                            consonant=None,
                            consonant_length=None,
                            vowel="cl",
                            vowel_length=6.5,
                            pitch=0.0,
                        ),
                        Mora(
                            text="ッ",
                            consonant=None,
                            consonant_length=None,
                            vowel="cl",
                            vowel_length=0.15,
                            pitch=0.3,
                        ),
                    ],
                    accent=1,
                    pause_mora=None,
                )
            ],
            enable_interrogative=True,
        )

        self.create_accent_phrases_test_base(
            text="っ？",
            expected=[
                AccentPhrase(
                    moras=[
                        Mora(
                            text="ッ",
                            consonant=None,
                            consonant_length=None,
                            vowel="cl",
                            vowel_length=6.5,
                            pitch=0.0,
                        ),
                    ],
                    accent=1,
                    pause_mora=None,
                )
            ],
            enable_interrogative=False,
        )

        self.create_accent_phrases_test_base(
            text="す",
            expected=[
                AccentPhrase(
                    moras=[
                        Mora(
                            text="ス",
                            consonant="s",
                            consonant_length=18.5,
                            vowel="u",
                            vowel_length=21.0,
                            pitch=40.5,
                        ),
                    ],
                    accent=1,
                    pause_mora=None,
                )
            ],
            enable_interrogative=True,
        )

        self.create_accent_phrases_test_base(
            text="す？",
            expected=[
                AccentPhrase(
                    moras=[
                        Mora(
                            text="ス",
                            consonant="s",
                            consonant_length=18.5,
                            vowel="u",
                            vowel_length=21.0,
                            pitch=40.0,
                        ),
                        Mora(
                            text="ウ",
                            consonant=None,
                            consonant_length=None,
                            vowel="u",
                            vowel_length=0.15,
                            pitch=6.5,
                        ),
                    ],
                    accent=1,
                    pause_mora=None,
                )
            ],
            enable_interrogative=True,
        )

        self.create_accent_phrases_test_base(
            text="す？",
            expected=[
                AccentPhrase(
                    moras=[
                        Mora(
                            text="ス",
                            consonant="s",
                            consonant_length=18.5,
                            vowel="u",
                            vowel_length=21.0,
                            pitch=40.5,
                        ),
                    ],
                    accent=1,
                    pause_mora=None,
                )
            ],
            enable_interrogative=False,
        )
