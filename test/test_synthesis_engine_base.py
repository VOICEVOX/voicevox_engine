from typing import List
from unittest import TestCase

from voicevox_engine.dev.synthesis_engine.mock import MockSynthesisEngine
from voicevox_engine.model import AccentPhrase, Mora


class TestSynthesisEngineBase(TestCase):
    def setUp(self):
        super().setUp()
        self.synthesis_engine = MockSynthesisEngine(speakers="")

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
        def koreha_arimasuka_base_expected():
            return [
                AccentPhrase(
                    moras=[
                        Mora(
                            text="コ",
                            consonant="k",
                            consonant_length=0,
                            vowel="o",
                            vowel_length=0,
                            pitch=0,
                        ),
                        Mora(
                            text="レ",
                            consonant="r",
                            consonant_length=0,
                            vowel="e",
                            vowel_length=0,
                            pitch=0,
                        ),
                        Mora(
                            text="ワ",
                            consonant="w",
                            consonant_length=0,
                            vowel="a",
                            vowel_length=0,
                            pitch=0,
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
                            vowel_length=0,
                            pitch=0,
                        ),
                        Mora(
                            text="リ",
                            consonant="r",
                            consonant_length=0,
                            vowel="i",
                            vowel_length=0,
                            pitch=0,
                        ),
                        Mora(
                            text="マ",
                            consonant="m",
                            consonant_length=0,
                            vowel="a",
                            vowel_length=0,
                            pitch=0,
                        ),
                        Mora(
                            text="ス",
                            consonant="s",
                            consonant_length=0,
                            vowel="U",
                            vowel_length=0,
                            pitch=0,
                        ),
                        Mora(
                            text="カ",
                            consonant="k",
                            consonant_length=0,
                            vowel="a",
                            vowel_length=0,
                            pitch=0,
                        ),
                    ],
                    accent=3,
                    pause_mora=None,
                ),
            ]

        expected = koreha_arimasuka_base_expected()
        expected[-1].moras += [
            Mora(
                text="ア",
                consonant=None,
                consonant_length=None,
                vowel="a",
                vowel_length=0.15,
                pitch=0.3,
            )
        ]
        self.create_accent_phrases_test_base(
            text="これはありますか？",
            expected=expected,
            enable_interrogative=True,
        )

        expected = koreha_arimasuka_base_expected()
        self.create_accent_phrases_test_base(
            text="これはありますか？",
            expected=expected,
            enable_interrogative=False,
        )

        expected = koreha_arimasuka_base_expected()
        self.create_accent_phrases_test_base(
            text="これはありますか",
            expected=expected,
            enable_interrogative=True,
        )

        def nn_base_expected():
            return [
                AccentPhrase(
                    moras=[
                        Mora(
                            text="ン",
                            consonant=None,
                            consonant_length=None,
                            vowel="N",
                            vowel_length=0,
                            pitch=0,
                        ),
                    ],
                    accent=1,
                    pause_mora=None,
                )
            ]

        expected = nn_base_expected()
        self.create_accent_phrases_test_base(
            text="ん",
            expected=expected,
            enable_interrogative=True,
        )

        expected = nn_base_expected()
        expected[-1].moras += [
            Mora(
                text="ン",
                consonant=None,
                consonant_length=None,
                vowel="N",
                vowel_length=0.15,
                pitch=0.3,
            )
        ]
        self.create_accent_phrases_test_base(
            text="ん？",
            expected=expected,
            enable_interrogative=True,
        )

        expected = nn_base_expected()
        self.create_accent_phrases_test_base(
            text="ん？",
            expected=expected,
            enable_interrogative=False,
        )

        def ltu_base_expected():
            return [
                AccentPhrase(
                    moras=[
                        Mora(
                            text="ッ",
                            consonant=None,
                            consonant_length=None,
                            vowel="cl",
                            vowel_length=0,
                            pitch=0.0,
                        ),
                    ],
                    accent=1,
                    pause_mora=None,
                )
            ]

        expected = ltu_base_expected()
        self.create_accent_phrases_test_base(
            text="っ",
            expected=expected,
            enable_interrogative=True,
        )

        expected = ltu_base_expected()
        expected[-1].moras += [
            Mora(
                text="ッ",
                consonant=None,
                consonant_length=None,
                vowel="cl",
                vowel_length=0.15,
                pitch=0.3,
            )
        ]
        self.create_accent_phrases_test_base(
            text="っ？",
            expected=expected,
            enable_interrogative=True,
        )

        expected = ltu_base_expected()
        self.create_accent_phrases_test_base(
            text="っ？",
            expected=expected,
            enable_interrogative=False,
        )

        def su_base_expected():
            return [
                AccentPhrase(
                    moras=[
                        Mora(
                            text="ス",
                            consonant="s",
                            consonant_length=0,
                            vowel="u",
                            vowel_length=0,
                            pitch=0,
                        ),
                    ],
                    accent=1,
                    pause_mora=None,
                )
            ]

        expected = su_base_expected()
        self.create_accent_phrases_test_base(
            text="す",
            expected=expected,
            enable_interrogative=True,
        )

        expected = su_base_expected()
        expected[-1].moras += [
            Mora(
                text="ウ",
                consonant=None,
                consonant_length=None,
                vowel="u",
                vowel_length=0.15,
                pitch=0.3,
            )
        ]
        self.create_accent_phrases_test_base(
            text="す？",
            expected=expected,
            enable_interrogative=True,
        )

        expected = su_base_expected()
        self.create_accent_phrases_test_base(
            text="す？",
            expected=expected,
            enable_interrogative=False,
        )
