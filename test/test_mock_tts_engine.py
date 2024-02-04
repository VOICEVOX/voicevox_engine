from unittest import TestCase

from voicevox_engine.dev.tts_engine.mock import MockTTSEngine
from voicevox_engine.metas.Metas import StyleId
from voicevox_engine.model import AccentPhrase, AudioQuery, Mora
from voicevox_engine.tts_pipeline.kana_converter import create_kana


def _gen_mora(text: str, consonant: str | None, vowel: str) -> Mora:
    """モーラ (length=0, pitch=0) を生成する"""
    return Mora(
        text=text,
        consonant=consonant,
        consonant_length=0.0 if consonant else None,
        vowel=vowel,
        vowel_length=0.0,
        pitch=0.0,
    )


class TestMockTTSEngine(TestCase):
    def setUp(self):
        super().setUp()

        self.accent_phrases_hello_hiho = [
            AccentPhrase(
                moras=[
                    _gen_mora("コ", "k", "o"),
                    _gen_mora("ン", None, "N"),
                    _gen_mora("ニ", "n", "i"),
                    _gen_mora("チ", "ch", "i"),
                    _gen_mora("ワ", "w", "a"),
                ],
                accent=5,
                pause_mora=_gen_mora("、", None, "pau"),
            ),
            AccentPhrase(
                moras=[
                    _gen_mora("ヒ", "h", "i"),
                    _gen_mora("ホ", "h", "o"),
                    _gen_mora("デ", "d", "e"),
                    _gen_mora("ス", "s", "U"),
                ],
                accent=1,
                pause_mora=None,
            ),
        ]
        self.engine = MockTTSEngine()

    def test_update_length(self):
        """`.update_length()` がエラー無く生成をおこなう"""
        self.engine.update_length(self.accent_phrases_hello_hiho, StyleId(0))

    def test_update_pitch(self):
        """`.update_pitch()` がエラー無く生成をおこなう"""
        self.engine.update_pitch(self.accent_phrases_hello_hiho, StyleId(0))

    def test_synthesize_wave(self):
        """`.synthesize_wave()` がエラー無く生成をおこなう"""
        self.engine.synthesize_wave(
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
            StyleId(0),
        )
