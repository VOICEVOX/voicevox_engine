import json
from typing import Union
from unittest import TestCase
from unittest.mock import Mock

import numpy
import pytest
from pydantic.json import pydantic_encoder
from syrupy.extensions.json import JSONSnapshotExtension

from voicevox_engine.dev.core.mock import MockCoreWrapper
from voicevox_engine.metas.Metas import StyleId
from voicevox_engine.model import AccentPhrase, Mora
from voicevox_engine.tts_pipeline.acoustic_feature_extractor import (
    UNVOICED_MORA_TAIL_PHONEMES,
    Phoneme,
)
from voicevox_engine.tts_pipeline.text_analyzer import text_to_accent_phrases
from voicevox_engine.tts_pipeline.tts_engine import (
    TTSEngine,
    apply_interrogative_upspeak,
    split_mora,
    to_flatten_moras,
    to_flatten_phonemes,
)

from .test_text_analyzer import stub_unknown_features_koxx

TRUE_NUM_PHONEME = 45


def is_same_phoneme(p1: Phoneme, p2: Phoneme) -> bool:
    """2つのPhonemeが同じ `.phoneme` を持つ"""
    return p1.phoneme == p2.phoneme


def yukarin_s_mock(
    length: int, phoneme_list: numpy.ndarray, style_id: numpy.ndarray
) -> numpy.ndarray:
    result = []
    # mockとしての適当な処理、特に意味はない
    for i in range(length):
        result.append(round((phoneme_list[i] * 0.0625 + style_id).item(), 2))
    return numpy.array(result)


def yukarin_sa_mock(
    length: int,
    vowel_phoneme_list: numpy.ndarray,
    consonant_phoneme_list: numpy.ndarray,
    start_accent_list: numpy.ndarray,
    end_accent_list: numpy.ndarray,
    start_accent_phrase_list: numpy.ndarray,
    end_accent_phrase_list: numpy.ndarray,
    style_id: numpy.ndarray,
) -> numpy.ndarray:
    result = []
    # mockとしての適当な処理、特に意味はない
    for i in range(length):
        result.append(
            round(
                (
                    (
                        vowel_phoneme_list[0][i]
                        + consonant_phoneme_list[0][i]
                        + start_accent_list[0][i]
                        + end_accent_list[0][i]
                        + start_accent_phrase_list[0][i]
                        + end_accent_phrase_list[0][i]
                    )
                    * 0.0625
                    + style_id
                ).item(),
                2,
            )
        )
    return numpy.array(result)[numpy.newaxis]


def decode_mock(
    length: int,
    phoneme_size: int,
    f0: numpy.ndarray,
    phoneme: numpy.ndarray,
    style_id: Union[numpy.ndarray, int],
) -> numpy.ndarray:
    result = []
    # mockとしての適当な処理、特に意味はない
    for i in range(length):
        result += [
            (f0[i, 0] * (numpy.where(phoneme[i] == 1)[0] / phoneme_size) + style_id)
        ] * 256
    return numpy.array(result)


class MockCore:
    default_sampling_rate = 24000
    yukarin_s_forward = Mock(side_effect=yukarin_s_mock)
    yukarin_sa_forward = Mock(side_effect=yukarin_sa_mock)
    decode_forward = Mock(side_effect=decode_mock)

    def metas(self):
        return ""

    def supported_devices(self):
        return ""

    def is_model_loaded(self, style_id):
        return True


def _gen_mora(
    text: str,
    consonant: str | None,
    consonant_length: float | None,
    vowel: str,
    vowel_length: float,
    pitch: float,
) -> Mora:
    """Generate Mora with positional arguments for test simplicity."""
    return Mora(
        text=text,
        consonant=consonant,
        consonant_length=consonant_length,
        vowel=vowel,
        vowel_length=vowel_length,
        pitch=pitch,
    )


def test_to_flatten_phonemes():
    """Test `to_flatten_phonemes`."""
    # Inputs
    moras = [
        _gen_mora("　", None, None, "sil", 2 * 0.01067, 0.0),
        _gen_mora("ヒ", "h", 2 * 0.01067, "i", 4 * 0.01067, 100.0),
        _gen_mora("　", None, None, "sil", 6 * 0.01067, 0.0),
    ]

    # Expects
    true_phonemes = ["pau", "h", "i", "pau"]

    # Outputs
    phonemes = list(map(lambda p: p.phoneme, to_flatten_phonemes(moras)))

    assert true_phonemes == phonemes


def _gen_hello_hiho_accent_phrases() -> list[AccentPhrase]:
    return [
        AccentPhrase(
            moras=[
                _gen_mora("コ", "k", 0.0, "o", 0.0, 0.0),
                _gen_mora("ン", None, None, "N", 0.0, 0.0),
                _gen_mora("ニ", "n", 0.0, "i", 0.0, 0.0),
                _gen_mora("チ", "ch", 0.0, "i", 0.0, 0.0),
                _gen_mora("ワ", "w", 0.0, "a", 0.0, 0.0),
            ],
            accent=5,
            pause_mora=_gen_mora("、", None, None, "pau", 0.0, 0.0),
        ),
        AccentPhrase(
            moras=[
                _gen_mora("ヒ", "h", 0.0, "i", 0.0, 0.0),
                _gen_mora("ホ", "h", 0.0, "o", 0.0, 0.0),
                _gen_mora("デ", "d", 0.0, "e", 0.0, 0.0),
                _gen_mora("ス", "s", 0.0, "U", 0.0, 0.0),
            ],
            accent=1,
            pause_mora=None,
        ),
    ]


def is_same_phonemes(
    p1s: list[Phoneme] | list[Phoneme | None], p2s: list[Phoneme] | list[Phoneme | None]
) -> bool:
    """2つのPhonemeリストで全要素ペアが同じ `.phoneme` を持つ"""
    if len(p1s) != len(p2s):
        return False

    for p1, p2 in zip(p1s, p2s):
        if p1 is None and p2 is None:  # None vs None -> equal
            pass
        elif p1 is None:  # None vs OjtOhoneme -> not equal
            return False
        elif p2 is None:  # OjtOhoneme vs None -> not equal
            return False
        elif is_same_phoneme(p1, p2):
            pass
        else:
            return False
    return True


def test_split_mora():
    # Inputs
    hello_hiho = "sil k o N n i ch i w a pau h i h o d e s U sil"
    hello_hiho_phonemes = [Phoneme(p) for p in hello_hiho.split()]
    # Outputs
    consonants, vowels = split_mora(hello_hiho_phonemes)
    # Expects
    cs = [None, "k", None, "n", "ch", "w", None, "h", "h", "d", "s", None]
    vs = ["pau", "o", "N", "i", "i", "a", "pau", "i", "o", "e", "U", "pau"]
    true_consonants = [Phoneme(p) if p else None for p in cs]
    true_vowels = [Phoneme(p) for p in vs]
    # Tests
    assert is_same_phonemes(vowels, true_vowels)
    assert is_same_phonemes(consonants, true_consonants)


class TestTTSEngine(TestCase):
    def setUp(self):
        super().setUp()
        core = MockCore()
        self.yukarin_s_mock = core.yukarin_s_forward
        self.yukarin_sa_mock = core.yukarin_sa_forward
        self.decode_mock = core.decode_forward
        self.tts_engine = TTSEngine(core=core)  # type: ignore[arg-type]

    def test_to_flatten_moras(self):
        flatten_moras = to_flatten_moras(_gen_hello_hiho_accent_phrases())
        true_accent_phrases_hello_hiho = _gen_hello_hiho_accent_phrases()
        self.assertEqual(
            flatten_moras,
            true_accent_phrases_hello_hiho[0].moras
            + [true_accent_phrases_hello_hiho[0].pause_mora]
            + true_accent_phrases_hello_hiho[1].moras,
        )

    def test_update_length(self):
        # Inputs
        hello_hiho = _gen_hello_hiho_accent_phrases()
        # Outputs & Indirect Outputs（yukarin_sに渡される値）
        result = self.tts_engine.update_length(hello_hiho, StyleId(1))
        yukarin_s_args = self.yukarin_s_mock.call_args[1]
        list_length = yukarin_s_args["length"]
        phoneme_list = yukarin_s_args["phoneme_list"]
        style_id = yukarin_s_args["style_id"]
        # Expects
        true_list_length = 20
        true_style_id = 1
        true_phoneme_list_1 = [0, 23, 30, 4, 28, 21, 10, 21, 42, 7]
        true_phoneme_list_2 = [0, 19, 21, 19, 30, 12, 14, 35, 6, 0]
        true_phoneme_list = true_phoneme_list_1 + true_phoneme_list_2
        true_result = _gen_hello_hiho_accent_phrases()
        index = 1

        def result_value(i: int) -> float:
            return round(float(phoneme_list[i] * 0.0625 + 1), 2)

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
        # Tests
        self.assertEqual(list_length, true_list_length)
        self.assertEqual(list_length, len(phoneme_list))
        self.assertEqual(style_id, true_style_id)
        numpy.testing.assert_array_equal(
            phoneme_list,
            numpy.array(true_phoneme_list, dtype=numpy.int64),
        )
        self.assertEqual(result, true_result)

    def test_update_pitch(self):
        # 空のリストでエラーを吐かないか
        # Inputs
        phrases: list = []
        # Outputs
        result = self.tts_engine.update_pitch(phrases, StyleId(1))
        # Expects
        true_result: list = []
        # Tests
        self.assertEqual(result, true_result)

        # Inputs
        hello_hiho = _gen_hello_hiho_accent_phrases()
        # Outputs & Indirect Outputs（yukarin_saに渡される値）
        result = self.tts_engine.update_pitch(hello_hiho, StyleId(1))
        yukarin_sa_args = self.yukarin_sa_mock.call_args[1]
        list_length = yukarin_sa_args["length"]
        vowel_phoneme_list = yukarin_sa_args["vowel_phoneme_list"][0]
        consonant_phoneme_list = yukarin_sa_args["consonant_phoneme_list"][0]
        start_accent_list = yukarin_sa_args["start_accent_list"][0]
        end_accent_list = yukarin_sa_args["end_accent_list"][0]
        start_accent_phrase_list = yukarin_sa_args["start_accent_phrase_list"][0]
        end_accent_phrase_list = yukarin_sa_args["end_accent_phrase_list"][0]
        style_id = yukarin_sa_args["style_id"]
        # Expects
        true_vowels = numpy.array([0, 30, 4, 21, 21, 7, 0, 21, 30, 14, 6, 0])
        true_consonants = numpy.array([-1, 23, -1, 28, 10, 42, -1, 19, 19, 12, 35, -1])
        true_accent_starts = numpy.array([0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0])
        true_accent_ends = numpy.array([0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0])
        true_phrase_starts = numpy.array([0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0])
        true_phrase_ends = numpy.array([0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0])
        true_result = _gen_hello_hiho_accent_phrases()
        index = 1

        def result_value(i: int) -> float:
            # unvoiced_vowel_likesのPhoneme ID版
            unvoiced_mora_tail_ids = [
                Phoneme(p).phoneme_id for p in UNVOICED_MORA_TAIL_PHONEMES
            ]
            if vowel_phoneme_list[i] in unvoiced_mora_tail_ids:
                return 0
            return round(
                (
                    (
                        vowel_phoneme_list[i]
                        + consonant_phoneme_list[i]
                        + start_accent_list[i]
                        + end_accent_list[i]
                        + start_accent_phrase_list[i]
                        + end_accent_phrase_list[i]
                    )
                    * 0.0625
                    + 1
                ),
                2,
            )

        for accent_phrase in true_result:
            moras = accent_phrase.moras
            for mora in moras:
                mora.pitch = result_value(index)
                index += 1
            if accent_phrase.pause_mora is not None:
                accent_phrase.pause_mora.pitch = result_value(index)
                index += 1
        # Tests
        self.assertEqual(list_length, 12)
        self.assertEqual(list_length, len(vowel_phoneme_list))
        self.assertEqual(list_length, len(consonant_phoneme_list))
        self.assertEqual(list_length, len(start_accent_list))
        self.assertEqual(list_length, len(end_accent_list))
        self.assertEqual(list_length, len(start_accent_phrase_list))
        self.assertEqual(list_length, len(end_accent_phrase_list))
        self.assertEqual(style_id, 1)
        numpy.testing.assert_array_equal(vowel_phoneme_list, true_vowels)
        numpy.testing.assert_array_equal(consonant_phoneme_list, true_consonants)
        numpy.testing.assert_array_equal(start_accent_list, true_accent_starts)
        numpy.testing.assert_array_equal(end_accent_list, true_accent_ends)
        numpy.testing.assert_array_equal(start_accent_phrase_list, true_phrase_starts)
        numpy.testing.assert_array_equal(end_accent_phrase_list, true_phrase_ends)
        self.assertEqual(result, true_result)


def test_create_accent_phrases_toward_unknown():
    """`TTSEngine.create_accent_phrases()` は unknown 音素の Phoneme 化に失敗する"""
    engine = TTSEngine(MockCoreWrapper())

    # NOTE: TTSEngine.create_accent_phrases() のコールで unknown feature を得ることが難しいため、疑似再現
    accent_phrases = text_to_accent_phrases(
        "dummy", text_to_features=stub_unknown_features_koxx
    )
    with pytest.raises(ValueError) as e:
        accent_phrases = engine.update_length_and_pitch(accent_phrases, StyleId(0))
    assert str(e.value) == "tuple.index(x): x not in tuple"


def test_mocked_update_length_output(snapshot_json: JSONSnapshotExtension) -> None:
    # Inputs
    tts_engine = TTSEngine(MockCoreWrapper())
    hello_hiho = _gen_hello_hiho_accent_phrases()
    # Outputs
    result = tts_engine.update_length(hello_hiho, StyleId(1))
    # Tests
    assert snapshot_json == json.loads(json.dumps(result, default=pydantic_encoder))


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
        self.tts_engine = TTSEngine(core=MockCoreWrapper())

    def create_synthesis_test_base(
        self,
        text: str,
        expected: list[AccentPhrase],
        enable_interrogative_upspeak: bool,
    ) -> None:
        """音声合成時に疑問文モーラ処理を行っているかどうかを検証
        (https://github.com/VOICEVOX/voicevox_engine/issues/272#issuecomment-1022610866)
        """
        inputs = self.tts_engine.create_accent_phrases(text, StyleId(1))
        outputs = apply_interrogative_upspeak(inputs, enable_interrogative_upspeak)
        self.assertEqual(expected, outputs, f"case(text:{text})")

    def test_create_accent_phrases(self):
        """accent_phrasesの作成時では疑問文モーラ処理を行わない
        (https://github.com/VOICEVOX/voicevox_engine/issues/272#issuecomment-1022610866)
        """
        text = "これはありますか？"
        expected = koreha_arimasuka_base_expected()
        expected[-1].is_interrogative = True
        actual = self.tts_engine.create_accent_phrases(text, StyleId(1))
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
