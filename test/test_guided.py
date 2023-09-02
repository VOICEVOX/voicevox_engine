import os
from unittest import TestCase

import soundfile as sf

from voicevox_engine.guided.extractor import extract
from voicevox_engine.model import AccentPhrase, AudioQuery, Mora


class TestGuided(TestCase):
    def setUp(self) -> None:
        self.audio_query: AudioQuery = AudioQuery(
            accent_phrases=[
                AccentPhrase(
                    moras=[
                        Mora(
                            text="モ",
                            consonant="m",
                            consonant_length=0.06260558217763901,
                            vowel="o",
                            vowel_length=0.08020618557929993,
                            pitch=5.664520263671875,
                        ),
                        Mora(
                            text="シ",
                            consonant="sh",
                            consonant_length=0.056903235614299774,
                            vowel="i",
                            vowel_length=0.08175592869520187,
                            pitch=5.879235744476318,
                        ),
                        Mora(
                            text="モ",
                            consonant="m",
                            consonant_length=0.06446344405412674,
                            vowel="o",
                            vowel_length=0.08384723961353302,
                            pitch=5.751187324523926,
                        ),
                        Mora(
                            text="オ",
                            consonant=None,
                            consonant_length=None,
                            vowel="o",
                            vowel_length=0.07894056290388107,
                            pitch=5.596571922302246,
                        ),
                        Mora(
                            text="シ",
                            consonant="sh",
                            consonant_length=0.10696915537118912,
                            vowel="i",
                            vowel_length=0.12177867442369461,
                            pitch=5.452928066253662,
                        ),
                    ],
                    accent=1,
                    pause_mora=Mora(
                        text="、",
                        consonant=None,
                        consonant_length=None,
                        vowel="pau",
                        vowel_length=0.3938804566860199,
                        pitch=0.0,
                    ),
                    is_interrogative=False,
                ),
                AccentPhrase(
                    moras=[
                        Mora(
                            text="キ",
                            consonant="k",
                            consonant_length=0.06701362878084183,
                            vowel="I",
                            vowel_length=0.060752518475055695,
                            pitch=0.0,
                        ),
                        Mora(
                            text="コ",
                            consonant="k",
                            consonant_length=0.08047571033239365,
                            vowel="o",
                            vowel_length=0.09941165894269943,
                            pitch=5.798135757446289,
                        ),
                        Mora(
                            text="エ",
                            consonant=None,
                            consonant_length=None,
                            vowel="e",
                            vowel_length=0.08397304266691208,
                            pitch=5.861576080322266,
                        ),
                        Mora(
                            text="テ",
                            consonant="t",
                            consonant_length=0.05847732722759247,
                            vowel="e",
                            vowel_length=0.05767367035150528,
                            pitch=5.913130283355713,
                        ),
                        Mora(
                            text="マ",
                            consonant="m",
                            consonant_length=0.05892116576433182,
                            vowel="a",
                            vowel_length=0.08303137868642807,
                            pitch=5.933863162994385,
                        ),
                        Mora(
                            text="ス",
                            consonant="s",
                            consonant_length=0.037269726395606995,
                            vowel="U",
                            vowel_length=0.07509166747331619,
                            pitch=0.0,
                        ),
                        Mora(
                            text="カ",
                            consonant="k",
                            consonant_length=0.08566848188638687,
                            vowel="a",
                            vowel_length=0.13803963363170624,
                            pitch=5.623557090759277,
                        ),
                    ],
                    accent=5,
                    pause_mora=None,
                    is_interrogative=False,
                ),
            ],
            speedScale=1.0,
            pitchScale=0.0,
            intonationScale=1.0,
            volumeScale=1.0,
            prePhonemeLength=0.1,
            postPhonemeLength=0.1,
            outputSamplingRate=24000,
            outputStereo=False,
            kana="モ'シモオシ、_キコエテマ'_スカ",
        )
        return super().setUp()

    def test_guided(self):
        root = os.getcwd()
        ref_path = os.path.join(root, "test", "ref_audio.wav")
        wav, sr = sf.read(ref_path)
        assert os.path.exists("cv_jp.bin"), "forced alignment model doesn't exist"
        extract(
            wav, sr, query=self.audio_query, model_path="cv_jp.bin"
        )  # as long as it doesn't throw exceptions it's okay
