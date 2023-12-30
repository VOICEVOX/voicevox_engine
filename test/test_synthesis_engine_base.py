from unittest import TestCase

from voicevox_engine.dev.core.mock import MockCoreWrapper
from voicevox_engine.model import AccentPhrase, Mora
from voicevox_engine.tts_pipeline import TTSEngine
from voicevox_engine.tts_pipeline.tts_engine import (
    apply_interrogative_upspeak,  # FIXME: この関数を使うテストをTTSEngine用のテストに移動する
)


def koreha_arimasuka_base_expected():
    return [
        AccentPhrase(
            moras=[
                Mora(
                    text="コ",
                    consonant="k",
                    consonant_length=2.44,
                    vowel="o",
                    vowel_length=2.88,
                    pitch=4.38,
                ),
                Mora(
                    text="レ",
                    consonant="r",
                    consonant_length=3.06,
                    vowel="e",
                    vowel_length=1.88,
                    pitch=4.0,
                ),
                Mora(
                    text="ワ",
                    consonant="w",
                    consonant_length=3.62,
                    vowel="a",
                    vowel_length=1.44,
                    pitch=4.19,
                ),
            ],
            accent=3,
            pause_mora=None,
            is_interrogative=False,
        ),
        AccentPhrase(
            moras=[
                Mora(
                    text="ア",
                    consonant=None,
                    consonant_length=None,
                    vowel="a",
                    vowel_length=1.44,
                    pitch=1.44,
                ),
                Mora(
                    text="リ",
                    consonant="r",
                    consonant_length=3.06,
                    vowel="i",
                    vowel_length=2.31,
                    pitch=4.44,
                ),
                Mora(
                    text="マ",
                    consonant="m",
                    consonant_length=2.62,
                    vowel="a",
                    vowel_length=1.44,
                    pitch=3.12,
                ),
                Mora(
                    text="ス",
                    consonant="s",
                    consonant_length=3.19,
                    vowel="U",
                    vowel_length=1.38,
                    pitch=0.0,
                ),
                Mora(
                    text="カ",
                    consonant="k",
                    consonant_length=2.44,
                    vowel="a",
                    vowel_length=1.44,
                    pitch=2.94,
                ),
            ],
            accent=3,
            pause_mora=None,
            is_interrogative=False,
        ),
    ]


class TestTTSEngineBase(TestCase):
    def setUp(self):
        super().setUp()
        self.synthesis_engine = TTSEngine(core=MockCoreWrapper())

    def create_synthesis_test_base(
        self,
        text: str,
        expected: list[AccentPhrase],
        enable_interrogative_upspeak: bool,
    ):
        """音声合成時に疑問文モーラ処理を行っているかどうかを検証
        (https://github.com/VOICEVOX/voicevox_engine/issues/272#issuecomment-1022610866)
        """
        inputs = self.synthesis_engine.create_accent_phrases(text, 1)
        outputs = apply_interrogative_upspeak(inputs, enable_interrogative_upspeak)
        self.assertEqual(expected, outputs, f"case(text:{text})")

    def test_create_accent_phrases(self):
        """accent_phrasesの作成時では疑問文モーラ処理を行わない
        (https://github.com/VOICEVOX/voicevox_engine/issues/272#issuecomment-1022610866)
        """
        text = "これはありますか？"
        expected = koreha_arimasuka_base_expected()
        expected[-1].is_interrogative = True
        actual = self.synthesis_engine.create_accent_phrases(text, 1)
        self.assertEqual(expected, actual, f"case(text:{text})")

    def test_upspeak_voiced_last_mora(self):
        # voiced + "？" + flagON -> upspeak
        expected = koreha_arimasuka_base_expected()
        expected[-1].is_interrogative = True
        expected[-1].moras += [
            Mora(
                text="ア",
                consonant=None,
                consonant_length=None,
                vowel="a",
                vowel_length=0.15,
                pitch=expected[-1].moras[-1].pitch + 0.3,
            )
        ]
        self.create_synthesis_test_base(
            text="これはありますか？",
            expected=expected,
            enable_interrogative_upspeak=True,
        )

        # voiced + "？" + flagOFF -> non-upspeak
        expected = koreha_arimasuka_base_expected()
        expected[-1].is_interrogative = True
        self.create_synthesis_test_base(
            text="これはありますか？",
            expected=expected,
            enable_interrogative_upspeak=False,
        )

        # voiced + "" + flagON -> non-upspeak
        expected = koreha_arimasuka_base_expected()
        self.create_synthesis_test_base(
            text="これはありますか",
            expected=expected,
            enable_interrogative_upspeak=True,
        )

    def test_upspeak_voiced_N_last_mora(self):
        def nn_base_expected():
            return [
                AccentPhrase(
                    moras=[
                        Mora(
                            text="ン",
                            consonant=None,
                            consonant_length=None,
                            vowel="N",
                            vowel_length=1.25,
                            pitch=1.44,
                        )
                    ],
                    accent=1,
                    pause_mora=None,
                    is_interrogative=False,
                )
            ]

        # voiced + "" + flagON -> upspeak
        expected = nn_base_expected()
        self.create_synthesis_test_base(
            text="ん",
            expected=expected,
            enable_interrogative_upspeak=True,
        )

        # voiced + "？" + flagON -> upspeak
        expected = nn_base_expected()
        expected[-1].is_interrogative = True
        expected[-1].moras += [
            Mora(
                text="ン",
                consonant=None,
                consonant_length=None,
                vowel="N",
                vowel_length=0.15,
                pitch=expected[-1].moras[-1].pitch + 0.3,
            )
        ]
        self.create_synthesis_test_base(
            text="ん？",
            expected=expected,
            enable_interrogative_upspeak=True,
        )

        # voiced + "？" + flagOFF -> non-upspeak
        expected = nn_base_expected()
        expected[-1].is_interrogative = True
        self.create_synthesis_test_base(
            text="ん？",
            expected=expected,
            enable_interrogative_upspeak=False,
        )

    def test_upspeak_unvoiced_last_mora(self):
        def ltu_base_expected():
            return [
                AccentPhrase(
                    moras=[
                        Mora(
                            text="ッ",
                            consonant=None,
                            consonant_length=None,
                            vowel="cl",
                            vowel_length=1.69,
                            pitch=0.0,
                        )
                    ],
                    accent=1,
                    pause_mora=None,
                    is_interrogative=False,
                )
            ]

        # unvoiced + "" + flagON -> non-upspeak
        expected = ltu_base_expected()
        self.create_synthesis_test_base(
            text="っ",
            expected=expected,
            enable_interrogative_upspeak=True,
        )

        # unvoiced + "？" + flagON -> non-upspeak
        expected = ltu_base_expected()
        expected[-1].is_interrogative = True
        self.create_synthesis_test_base(
            text="っ？",
            expected=expected,
            enable_interrogative_upspeak=True,
        )

        # unvoiced + "？" + flagOFF -> non-upspeak
        expected = ltu_base_expected()
        expected[-1].is_interrogative = True
        self.create_synthesis_test_base(
            text="っ？",
            expected=expected,
            enable_interrogative_upspeak=False,
        )

    def test_upspeak_voiced_u_last_mora(self):
        def su_base_expected():
            return [
                AccentPhrase(
                    moras=[
                        Mora(
                            text="ス",
                            consonant="s",
                            consonant_length=3.19,
                            vowel="u",
                            vowel_length=3.5,
                            pitch=5.94,
                        )
                    ],
                    accent=1,
                    pause_mora=None,
                    is_interrogative=False,
                )
            ]

        # voiced + "" + flagON -> non-upspeak
        expected = su_base_expected()
        self.create_synthesis_test_base(
            text="す",
            expected=expected,
            enable_interrogative_upspeak=True,
        )

        # voiced + "？" + flagON -> upspeak
        expected = su_base_expected()
        expected[-1].is_interrogative = True
        expected[-1].moras += [
            Mora(
                text="ウ",
                consonant=None,
                consonant_length=None,
                vowel="u",
                vowel_length=0.15,
                pitch=expected[-1].moras[-1].pitch + 0.3,
            )
        ]
        self.create_synthesis_test_base(
            text="す？",
            expected=expected,
            enable_interrogative_upspeak=True,
        )

        # voiced + "？" + flagOFF -> non-upspeak
        expected = su_base_expected()
        expected[-1].is_interrogative = True
        self.create_synthesis_test_base(
            text="す？",
            expected=expected,
            enable_interrogative_upspeak=False,
        )
