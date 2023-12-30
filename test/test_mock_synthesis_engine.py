from unittest import TestCase

from voicevox_engine.dev.core import MockCoreWrapper
from voicevox_engine.dev.tts_engine import MockTTSEngine
from voicevox_engine.model import AccentPhrase, AudioQuery, Mora
from voicevox_engine.tts_pipeline.kana_converter import create_kana


class TestMockTTSEngine(TestCase):
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
        self.engine = MockTTSEngine(MockCoreWrapper())

    def test_replace_phoneme_length(self):
        """`.replace_phoneme_length()` がエラー無く生成をおこなう"""
        self.engine.replace_phoneme_length(
            accent_phrases=self.accent_phrases_hello_hiho,
            style_id=0,
        )

    def test_replace_mora_pitch(self):
        """`.replace_mora_pitch()` がエラー無く生成をおこなう"""
        self.engine.replace_mora_pitch(
            accent_phrases=self.accent_phrases_hello_hiho,
            style_id=0,
        )

    def test_synthesis(self):
        """`.synthesis()` がエラー無く生成をおこなう"""
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
