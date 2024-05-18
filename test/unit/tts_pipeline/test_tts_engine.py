import json
from test.utility import pydantic_to_native_type, round_floats
from unittest import TestCase
from unittest.mock import Mock

import numpy as np
import pytest
from numpy.typing import NDArray
from syrupy.assertion import SnapshotAssertion

from voicevox_engine.dev.core.mock import MockCoreWrapper
from voicevox_engine.metas.Metas import StyleId
from voicevox_engine.model import (
    AccentPhrase,
    AudioQuery,
    FrameAudioQuery,
    Mora,
    Note,
    Score,
)
from voicevox_engine.tts_pipeline.text_analyzer import text_to_accent_phrases
from voicevox_engine.tts_pipeline.tts_engine import (
    TTSEngine,
    apply_interrogative_upspeak,
    to_flatten_moras,
    to_flatten_phonemes,
)

from .test_text_analyzer import stub_unknown_features_koxx


def yukarin_s_mock(
    length: int, phoneme_list: NDArray[np.int64], style_id: NDArray[np.int64]
) -> NDArray[np.float32]:
    result = []
    # mockとしての適当な処理、特に意味はない
    for i in range(length):
        result.append(round((phoneme_list[i] * 0.0625 + style_id).item(), 2))
    return np.array(result, dtype=np.float32)


def yukarin_sa_mock(
    length: int,
    vowel_phoneme_list: NDArray[np.int64],
    consonant_phoneme_list: NDArray[np.int64],
    start_accent_list: NDArray[np.int64],
    end_accent_list: NDArray[np.int64],
    start_accent_phrase_list: NDArray[np.int64],
    end_accent_phrase_list: NDArray[np.int64],
    style_id: NDArray[np.int64],
) -> NDArray[np.float32]:
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
    return np.array(result, dtype=np.float32)[np.newaxis]


def decode_mock(
    length: int,
    phoneme_size: int,
    f0: NDArray[np.float32],
    phoneme: NDArray[np.float32],
    style_id: NDArray[np.int64],
) -> NDArray[np.float32]:
    result = []
    # mockとしての適当な処理、特に意味はない
    for i in range(length):
        result += [
            (f0[i, 0] * (np.where(phoneme[i] == 1)[0] / phoneme_size) + style_id)
        ] * 256
    return np.array(result, dtype=np.float32)


class MockCore:
    default_sampling_rate = 24000
    yukarin_s_forward = Mock(side_effect=yukarin_s_mock)
    yukarin_sa_forward = Mock(side_effect=yukarin_sa_mock)
    decode_forward = Mock(side_effect=decode_mock)

    def metas(self) -> str:
        return ""

    def supported_devices(self) -> str:
        return json.dumps({"cpu": True, "cuda": False, "dml": False})

    def is_model_loaded(self, style_id: str) -> bool:
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


def test_to_flatten_phonemes() -> None:
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
    phonemes = list(map(lambda p: p._phoneme, to_flatten_phonemes(moras)))

    assert true_phonemes == phonemes


def _gen_hello_hiho_text() -> str:
    return "こんにちは、ヒホです"


def _gen_hello_hiho_kana() -> str:
    return "コンニチワ'、ヒ'ホデ_ス"


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


def _gen_hello_hiho_query() -> AudioQuery:
    return AudioQuery(
        accent_phrases=_gen_hello_hiho_accent_phrases(),
        speedScale=2.0,
        pitchScale=1.1,
        intonationScale=0.9,
        volumeScale=1.3,
        prePhonemeLength=0.1,
        postPhonemeLength=0.2,
        outputSamplingRate=12000,
        outputStereo=True,
        kana=_gen_hello_hiho_kana(),
    )


def _gen_doremi_score() -> Score:
    return Score(
        notes=[
            Note(key=None, frame_length=10, lyric=""),
            Note(key=60, frame_length=12, lyric="ど"),
            Note(key=62, frame_length=17, lyric="れ"),
            Note(key=64, frame_length=21, lyric="み"),
            Note(key=None, frame_length=5, lyric=""),
            Note(key=65, frame_length=12, lyric="ふぁ"),
            Note(key=67, frame_length=17, lyric="そ"),
            Note(key=None, frame_length=10, lyric=""),
        ]
    )


class TestTTSEngine(TestCase):
    def setUp(self) -> None:
        super().setUp()
        core = MockCore()
        self.yukarin_s_mock = core.yukarin_s_forward
        self.yukarin_sa_mock = core.yukarin_sa_forward
        self.decode_mock = core.decode_forward
        self.tts_engine = TTSEngine(core=core)  # type: ignore[arg-type]

    def test_to_flatten_moras(self) -> None:
        flatten_moras = to_flatten_moras(_gen_hello_hiho_accent_phrases())
        true_accent_phrases_hello_hiho = _gen_hello_hiho_accent_phrases()
        self.assertEqual(
            flatten_moras,
            true_accent_phrases_hello_hiho[0].moras
            + [true_accent_phrases_hello_hiho[0].pause_mora]
            + true_accent_phrases_hello_hiho[1].moras,
        )

    def test_update_length(self) -> None:
        # Inputs
        hello_hiho = _gen_hello_hiho_accent_phrases()
        # Indirect Outputs（yukarin_sに渡される値）
        self.tts_engine.update_length(hello_hiho, StyleId(1))
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

        self.assertEqual(list_length, true_list_length)
        self.assertEqual(list_length, len(phoneme_list))
        self.assertEqual(style_id, true_style_id)
        np.testing.assert_array_equal(
            phoneme_list,
            np.array(true_phoneme_list, dtype=np.int64),
        )

    def test_update_pitch(self) -> None:
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
        # Indirect Outputs（yukarin_saに渡される値）
        self.tts_engine.update_pitch(hello_hiho, StyleId(1))
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
        true_vowels = np.array([0, 30, 4, 21, 21, 7, 0, 21, 30, 14, 6, 0])
        true_consonants = np.array([-1, 23, -1, 28, 10, 42, -1, 19, 19, 12, 35, -1])
        true_accent_starts = np.array([0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0])
        true_accent_ends = np.array([0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0])
        true_phrase_starts = np.array([0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0])
        true_phrase_ends = np.array([0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0])

        # Tests
        self.assertEqual(list_length, 12)
        self.assertEqual(list_length, len(vowel_phoneme_list))
        self.assertEqual(list_length, len(consonant_phoneme_list))
        self.assertEqual(list_length, len(start_accent_list))
        self.assertEqual(list_length, len(end_accent_list))
        self.assertEqual(list_length, len(start_accent_phrase_list))
        self.assertEqual(list_length, len(end_accent_phrase_list))
        self.assertEqual(style_id, 1)
        np.testing.assert_array_equal(vowel_phoneme_list, true_vowels)
        np.testing.assert_array_equal(consonant_phoneme_list, true_consonants)
        np.testing.assert_array_equal(start_accent_list, true_accent_starts)
        np.testing.assert_array_equal(end_accent_list, true_accent_ends)
        np.testing.assert_array_equal(start_accent_phrase_list, true_phrase_starts)
        np.testing.assert_array_equal(end_accent_phrase_list, true_phrase_ends)


def test_create_accent_phrases_toward_unknown() -> None:
    """`TTSEngine.create_accent_phrases()` は unknown 音素の Phoneme 化に失敗する"""
    engine = TTSEngine(MockCoreWrapper())

    # NOTE: TTSEngine.create_accent_phrases() のコールで unknown feature を得ることが難しいため、疑似再現
    accent_phrases = text_to_accent_phrases(
        "dummy", text_to_features=stub_unknown_features_koxx
    )
    with pytest.raises(ValueError) as e:
        accent_phrases = engine.update_length_and_pitch(accent_phrases, StyleId(0))
    assert str(e.value) == "tuple.index(x): x not in tuple"


def test_mocked_update_length_output(snapshot_json: SnapshotAssertion) -> None:
    """モックされた `TTSEngine.update_length()` の出力スナップショットが一定である"""
    # Inputs
    tts_engine = TTSEngine(MockCoreWrapper())
    hello_hiho = _gen_hello_hiho_accent_phrases()
    # Outputs
    result = tts_engine.update_length(hello_hiho, StyleId(1))
    # Tests
    assert snapshot_json == round_floats(pydantic_to_native_type(result), round_value=2)


def test_mocked_update_pitch_output(snapshot_json: SnapshotAssertion) -> None:
    """モックされた `TTSEngine.update_pitch()` の出力スナップショットが一定である"""
    # Inputs
    tts_engine = TTSEngine(MockCoreWrapper())
    hello_hiho = _gen_hello_hiho_accent_phrases()
    # Outputs
    result = tts_engine.update_pitch(hello_hiho, StyleId(1))
    # Tests
    assert snapshot_json == round_floats(pydantic_to_native_type(result), round_value=2)


def test_mocked_update_length_and_pitch_output(
    snapshot_json: SnapshotAssertion,
) -> None:
    """モックされた `TTSEngine.update_length_and_pitch()` の出力スナップショットが一定である"""
    # Inputs
    tts_engine = TTSEngine(MockCoreWrapper())
    hello_hiho = _gen_hello_hiho_accent_phrases()
    # Outputs
    result = tts_engine.update_length_and_pitch(hello_hiho, StyleId(1))
    # Tests
    assert snapshot_json == round_floats(pydantic_to_native_type(result), round_value=2)


def test_mocked_create_accent_phrases_output(
    snapshot_json: SnapshotAssertion,
) -> None:
    """モックされた `TTSEngine.create_accent_phrases()` の出力スナップショットが一定である"""
    # Inputs
    tts_engine = TTSEngine(MockCoreWrapper())
    hello_hiho = _gen_hello_hiho_text()
    # Outputs
    result = tts_engine.create_accent_phrases(hello_hiho, StyleId(1))
    # Tests
    assert snapshot_json == round_floats(pydantic_to_native_type(result), round_value=2)


def test_mocked_create_accent_phrases_from_kana_output(
    snapshot_json: SnapshotAssertion,
) -> None:
    """モックされた `TTSEngine.create_accent_phrases_from_kana()` の出力スナップショットが一定である"""
    # Inputs
    tts_engine = TTSEngine(MockCoreWrapper())
    hello_hiho = _gen_hello_hiho_kana()
    # Outputs
    result = tts_engine.create_accent_phrases_from_kana(hello_hiho, StyleId(1))
    # Tests
    assert snapshot_json == round_floats(pydantic_to_native_type(result), round_value=2)


def test_mocked_synthesize_wave_output(snapshot_json: SnapshotAssertion) -> None:
    """モックされた `TTSEngine.synthesize_wave()` の出力スナップショットが一定である"""
    # Inputs
    tts_engine = TTSEngine(MockCoreWrapper())
    hello_hiho = _gen_hello_hiho_query()
    # Outputs
    result = tts_engine.synthesize_wave(hello_hiho, StyleId(1))
    # Tests
    assert snapshot_json == round_floats(result.tolist(), round_value=2)


def test_mocked_create_sing_volume_from_phoneme_and_f0_output(
    snapshot_json: SnapshotAssertion,
) -> None:
    """
    モックされた `TTSEngine.create_sing_phoneme_and_f0_and_volume()` の出力スナップショットが一定である
    NOTE: 入力生成の簡略化に別関数を呼び出すため、別関数が正しく動作しない場合テストが落ちる
    """
    # Inputs
    tts_engine = TTSEngine(MockCoreWrapper())
    doremi_srore = _gen_doremi_score()
    phonemes, f0s, _ = tts_engine.create_sing_phoneme_and_f0_and_volume(
        doremi_srore, StyleId(1)
    )
    # Outputs
    result = tts_engine.create_sing_volume_from_phoneme_and_f0(
        doremi_srore, phonemes, f0s, StyleId(1)
    )
    # Tests
    assert snapshot_json == round_floats(result, round_value=2)


def test_mocked_synthesize_wave_from_score_output(
    snapshot_json: SnapshotAssertion,
) -> None:
    """
    モックされた `TTSEngine.create_sing_phoneme_and_f0_and_volume()` と
    `TTSEngine.frame_synthsize_wave()` の出力スナップショットが一定である
    """
    # Inputs
    tts_engine = TTSEngine(MockCoreWrapper())
    doremi_srore = _gen_doremi_score()
    # Outputs
    result = tts_engine.create_sing_phoneme_and_f0_and_volume(doremi_srore, StyleId(1))
    # Tests
    assert snapshot_json(name="query") == round_floats(
        pydantic_to_native_type(result), round_value=2
    )

    # Inputs
    phonemes, f0, volume = result
    doremi_query = FrameAudioQuery(
        f0=f0,
        volume=volume,
        phonemes=phonemes,
        volumeScale=1.3,
        outputSamplingRate=1200,
        outputStereo=False,
    )
    # Outputs
    result_wave = tts_engine.frame_synthsize_wave(doremi_query, StyleId(1))
    # Tests
    assert snapshot_json(name="wave") == round_floats(
        result_wave.tolist(), round_value=2
    )


def koreha_arimasuka_base_expected() -> list[AccentPhrase]:
    return [
        AccentPhrase(
            moras=[
                Mora(
                    text="コ",
                    consonant="k",
                    consonant_length=np.float32(2.44),
                    vowel="o",
                    vowel_length=np.float32(2.88),
                    pitch=np.float32(4.38),
                ),
                Mora(
                    text="レ",
                    consonant="r",
                    consonant_length=np.float32(3.06),
                    vowel="e",
                    vowel_length=np.float32(1.88),
                    pitch=np.float32(4.0),
                ),
                Mora(
                    text="ワ",
                    consonant="w",
                    consonant_length=np.float32(3.62),
                    vowel="a",
                    vowel_length=np.float32(1.44),
                    pitch=np.float32(4.19),
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
                    vowel_length=np.float32(1.44),
                    pitch=np.float32(1.44),
                ),
                Mora(
                    text="リ",
                    consonant="r",
                    consonant_length=np.float32(3.06),
                    vowel="i",
                    vowel_length=np.float32(2.31),
                    pitch=np.float32(4.44),
                ),
                Mora(
                    text="マ",
                    consonant="m",
                    consonant_length=np.float32(2.62),
                    vowel="a",
                    vowel_length=np.float32(1.44),
                    pitch=np.float32(3.12),
                ),
                Mora(
                    text="ス",
                    consonant="s",
                    consonant_length=np.float32(3.19),
                    vowel="U",
                    vowel_length=np.float32(1.38),
                    pitch=np.float32(0.0),
                ),
                Mora(
                    text="カ",
                    consonant="k",
                    consonant_length=np.float32(2.44),
                    vowel="a",
                    vowel_length=np.float32(1.44),
                    pitch=np.float32(2.94),
                ),
            ],
            accent=3,
            pause_mora=None,
            is_interrogative=False,
        ),
    ]


class TestTTSEngineBase(TestCase):
    def setUp(self) -> None:
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

    def test_create_accent_phrases(self) -> None:
        """accent_phrasesの作成時では疑問文モーラ処理を行わない
        (https://github.com/VOICEVOX/voicevox_engine/issues/272#issuecomment-1022610866)
        """
        text = "これはありますか？"
        expected = koreha_arimasuka_base_expected()
        expected[-1].is_interrogative = True
        actual = self.tts_engine.create_accent_phrases(text, StyleId(1))
        self.assertEqual(expected, actual, f"case(text:{text})")

    def test_upspeak_voiced_last_mora(self) -> None:
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
                pitch=np.float32(expected[-1].moras[-1].pitch) + 0.3,
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

    def test_upspeak_voiced_N_last_mora(self) -> None:
        def nn_base_expected() -> list[AccentPhrase]:
            return [
                AccentPhrase(
                    moras=[
                        Mora(
                            text="ン",
                            consonant=None,
                            consonant_length=None,
                            vowel="N",
                            vowel_length=np.float32(1.25),
                            pitch=np.float32(1.44),
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
                pitch=np.float32(expected[-1].moras[-1].pitch) + 0.3,
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

    def test_upspeak_unvoiced_last_mora(self) -> None:
        def ltu_base_expected() -> list[AccentPhrase]:
            return [
                AccentPhrase(
                    moras=[
                        Mora(
                            text="ッ",
                            consonant=None,
                            consonant_length=None,
                            vowel="cl",
                            vowel_length=np.float32(1.69),
                            pitch=np.float32(0.0),
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

    def test_upspeak_voiced_u_last_mora(self) -> None:
        def su_base_expected() -> list[AccentPhrase]:
            return [
                AccentPhrase(
                    moras=[
                        Mora(
                            text="ス",
                            consonant="s",
                            consonant_length=np.float32(3.19),
                            vowel="u",
                            vowel_length=np.float32(3.5),
                            pitch=np.float32(5.94),
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
