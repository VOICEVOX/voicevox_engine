from unittest import TestCase

from voicevox_engine.dev.synthesis_engine import MockSynthesisEngine
from voicevox_engine.kana_parser import create_kana
from voicevox_engine.model import AccentPhrase, AudioQuery, Mora


class TestMockSynthesisEngine(TestCase):
    def setUp(self):
        super().setUp()

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
        self.engine = MockSynthesisEngine(speakers="", supported_devices="")

    def test_replace_phoneme_length(self):
        self.assertEqual(
            self.engine.replace_phoneme_length(
                accent_phrases=self.accent_phrases_hello_hiho,
                style_id=0,
            ),
            self.accent_phrases_hello_hiho,
        )

    def test_replace_mora_pitch(self):
        self.assertEqual(
            self.engine.replace_mora_pitch(
                accent_phrases=self.accent_phrases_hello_hiho,
                style_id=0,
            ),
            self.accent_phrases_hello_hiho,
        )

    def test_synthesis(self):
        self.engine.synthesis(
            AudioQuery(
                accent_phrases=self.accent_phrases_hello_hiho,
                speedScale=1,
                pitchScale=0,
                intonationScale=1,
                volumeScale=1,
                prePhonemeLength=0.1,
                postPhonemeLength=0.1,
                outputSamplingRate=24000,
                outputStereo=False,
                kana=create_kana(self.accent_phrases_hello_hiho),
            ),
            style_id=0,
        )
