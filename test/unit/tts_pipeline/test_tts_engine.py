"""TTSEngine のテスト"""

from test.utility import pydantic_to_native_type, round_floats, summarize_big_ndarray
from unittest.mock import MagicMock

import numpy as np
import pytest
from syrupy.assertion import SnapshotAssertion

from voicevox_engine.dev.core.mock import MockCoreWrapper
from voicevox_engine.metas.Metas import StyleId
from voicevox_engine.model import AudioQuery
from voicevox_engine.tts_pipeline.model import (
    AccentPhrase,
    FrameAudioQuery,
    Mora,
    Note,
    Score,
)
from voicevox_engine.tts_pipeline.text_analyzer import text_to_accent_phrases
from voicevox_engine.tts_pipeline.tts_engine import (
    TTSEngine,
    _apply_interrogative_upspeak,
    _to_flatten_phonemes,
    to_flatten_moras,
)

from .test_text_analyzer import stub_unknown_features_koxx
from .tts_utils import gen_mora, sec


def test_to_flatten_phonemes() -> None:
    """Test `_to_flatten_phonemes()`."""
    # Inputs
    moras = [
        gen_mora("　", None, None, "sil", sec(2), 0.0),
        gen_mora("ヒ", "h", sec(2), "i", sec(4), 5.0),
        gen_mora("　", None, None, "sil", sec(6), 0.0),
    ]
    # Expects
    true_phoneme_strs = ["pau", "h", "i", "pau"]
    # Outputs
    phonemes = _to_flatten_phonemes(moras)
    phoneme_strs = list(map(lambda p: p._phoneme, phonemes))

    # Test
    assert true_phoneme_strs == phoneme_strs


def _gen_hello_hiho_accent_phrases() -> list[AccentPhrase]:
    return [
        AccentPhrase(
            moras=[
                gen_mora("コ", "k", 0.1, "o", 0.1, 5.0),
                gen_mora("ン", None, None, "N", 0.1, 5.0),
                gen_mora("ニ", "n", 0.1, "i", 0.1, 5.0),
                gen_mora("チ", "ch", 0.1, "i", 0.1, 5.0),
                gen_mora("ワ", "w", 0.1, "a", 0.1, 5.0),
            ],
            accent=5,
            pause_mora=gen_mora("、", None, None, "pau", 0.1, 0.0),
        ),
        AccentPhrase(
            moras=[
                gen_mora("ヒ", "h", 0.1, "i", 0.1, 0.0),
                gen_mora("ホ", "h", 0.1, "o", 0.1, 5.0),
                gen_mora("デ", "d", 0.1, "e", 0.1, 5.0),
                gen_mora("ス", "s", 0.1, "U", 0.1, 0.0),
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
        pauseLength=0.3,
        pauseLengthScale=0.8,
        outputSamplingRate=12000,
        outputStereo=True,
        kana="コンニチワ'、ヒ'ホデ_ス",
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


def test_to_flatten_moras() -> None:
    flatten_moras = to_flatten_moras(_gen_hello_hiho_accent_phrases())
    true_accent_phrases_hello_hiho = _gen_hello_hiho_accent_phrases()
    assert (
        flatten_moras
        == true_accent_phrases_hello_hiho[0].moras
        + [true_accent_phrases_hello_hiho[0].pause_mora]
        + true_accent_phrases_hello_hiho[1].moras
    )


def test_update_length() -> None:
    core = MockCoreWrapper()
    core.yukarin_s_forward = MagicMock(wraps=core.yukarin_s_forward)  # type: ignore[method-assign]
    _yukarin_s_mock = core.yukarin_s_forward
    tts_engine = TTSEngine(core=core)
    # Inputs
    hello_hiho = _gen_hello_hiho_accent_phrases()
    # Indirect Outputs（yukarin_sに渡される値）
    tts_engine.update_length(hello_hiho, StyleId(1))
    yukarin_s_args = _yukarin_s_mock.call_args[1]
    list_length = yukarin_s_args["length"]
    phoneme_list = yukarin_s_args["phoneme_list"]
    style_id = yukarin_s_args["style_id"]
    # Expects
    true_list_length = 20
    true_style_id = 1
    true_phoneme_list_1 = [0, 23, 30, 4, 28, 21, 10, 21, 42, 7]
    true_phoneme_list_2 = [0, 19, 21, 19, 30, 12, 14, 35, 6, 0]
    true_phoneme_list = true_phoneme_list_1 + true_phoneme_list_2

    assert list_length == true_list_length
    assert list_length == len(phoneme_list)
    assert style_id == true_style_id
    np.testing.assert_array_equal(
        phoneme_list,
        np.array(true_phoneme_list, dtype=np.int64),
    )


def test_update_pitch() -> None:
    core = MockCoreWrapper()
    core.yukarin_sa_forward = MagicMock(wraps=core.yukarin_sa_forward)  # type: ignore[method-assign]
    _yukarin_sa_mock = core.yukarin_sa_forward
    tts_engine = TTSEngine(core=core)

    # 空のリストでエラーを吐かないか
    # Inputs
    phrases: list = []
    # Outputs
    result = tts_engine.update_pitch(phrases, StyleId(1))
    # Expects
    true_result: list = []
    # Tests
    assert result == true_result

    # Inputs
    hello_hiho = _gen_hello_hiho_accent_phrases()
    # Indirect Outputs（yukarin_saに渡される値）
    tts_engine.update_pitch(hello_hiho, StyleId(1))
    yukarin_sa_args = _yukarin_sa_mock.call_args[1]
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
    assert list_length == 12
    assert list_length == len(vowel_phoneme_list)
    assert list_length == len(consonant_phoneme_list)
    assert list_length == len(start_accent_list)
    assert list_length == len(end_accent_list)
    assert list_length == len(start_accent_phrase_list)
    assert list_length == len(end_accent_phrase_list)
    assert style_id == 1
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
    hello_hiho = "こんにちは、ヒホです"
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
    hello_hiho = "コンニチワ'、ヒ'ホデ_ス"
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
    assert snapshot_json == summarize_big_ndarray(round_floats(result, round_value=2))


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


def create_synthesis_test_base(text: str) -> list[AccentPhrase]:
    tts_engine = TTSEngine(core=MockCoreWrapper())
    return tts_engine.create_accent_phrases(text, StyleId(1))


def test_create_accent_phrases() -> None:
    """accent_phrasesの作成時では疑問文モーラ処理を行わない
    (https://github.com/VOICEVOX/voicevox_engine/issues/272#issuecomment-1022610866)
    """
    tts_engine = TTSEngine(core=MockCoreWrapper())
    text = "これはありますか？"
    expected = koreha_arimasuka_base_expected()
    expected[-1].is_interrogative = True
    actual = tts_engine.create_accent_phrases(text, StyleId(1))
    assert expected == actual, f"case(text:{text})"


def test_upspeak_voiced_last_mora() -> None:
    # voiced + "？" + flagON -> upspeak
    # Inputs
    inputs = create_synthesis_test_base(text="これはありますか？")
    # Expects
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
    # Outputs
    outputs = _apply_interrogative_upspeak(inputs, True)
    # Test
    assert expected == outputs

    # voiced + "？" + flagOFF -> non-upspeak
    # Inputs
    inputs = create_synthesis_test_base(text="これはありますか？")
    # Expects
    expected = koreha_arimasuka_base_expected()
    expected[-1].is_interrogative = True
    # Outputs
    outputs = _apply_interrogative_upspeak(inputs, False)
    # Test
    assert expected == outputs

    # voiced + "" + flagON -> non-upspeak
    # Inputs
    inputs = create_synthesis_test_base(text="これはありますか")
    # Expects
    expected = koreha_arimasuka_base_expected()
    # Outputs
    outputs = _apply_interrogative_upspeak(inputs, True)
    # Test
    assert expected == outputs


def test_upspeak_voiced_N_last_mora() -> None:
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
    # Inputs
    inputs = create_synthesis_test_base(text="ん")
    # Expects
    expected = nn_base_expected()
    # Outputs
    outputs = _apply_interrogative_upspeak(inputs, True)
    # Test
    assert expected == outputs

    # voiced + "？" + flagON -> upspeak
    # Inputs
    inputs = create_synthesis_test_base(text="ん？")
    # Expects
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
    # Outputs
    outputs = _apply_interrogative_upspeak(inputs, True)
    # Test
    assert expected == outputs

    # voiced + "？" + flagOFF -> non-upspeak
    # Inputs
    inputs = create_synthesis_test_base(text="ん？")
    # Expects
    expected = nn_base_expected()
    expected[-1].is_interrogative = True
    # Outputs
    outputs = _apply_interrogative_upspeak(inputs, False)
    # Test
    assert expected == outputs


def test_upspeak_unvoiced_last_mora() -> None:
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
    # Inputs
    inputs = create_synthesis_test_base(text="っ")
    # Expects
    expected = ltu_base_expected()
    # Outputs
    outputs = _apply_interrogative_upspeak(inputs, True)
    # Test
    assert expected == outputs

    # unvoiced + "？" + flagON -> non-upspeak
    # Inputs
    inputs = create_synthesis_test_base(text="っ？")
    # Expects
    expected = ltu_base_expected()
    expected[-1].is_interrogative = True
    # Outputs
    outputs = _apply_interrogative_upspeak(inputs, True)
    # Test
    assert expected == outputs

    # unvoiced + "？" + flagOFF -> non-upspeak
    # Inputs
    inputs = create_synthesis_test_base(text="っ？")
    # Expects
    expected = ltu_base_expected()
    expected[-1].is_interrogative = True
    # Outputs
    outputs = _apply_interrogative_upspeak(inputs, False)
    # Test
    assert expected == outputs


def test_upspeak_voiced_u_last_mora() -> None:
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
    # Inputs
    inputs = create_synthesis_test_base(text="す")
    # Expects
    expected = su_base_expected()
    # Outputs
    outputs = _apply_interrogative_upspeak(inputs, True)
    # Test
    assert expected == outputs

    # voiced + "？" + flagON -> upspeak
    # Inputs
    inputs = create_synthesis_test_base(text="す？")
    # Expects
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
    # Outputs
    outputs = _apply_interrogative_upspeak(inputs, True)
    # Test
    assert expected == outputs

    # voiced + "？" + flagOFF -> non-upspeak
    # Inputs
    inputs = create_synthesis_test_base(text="す？")
    # Expects
    expected = su_base_expected()
    expected[-1].is_interrogative = True
    # Outputs
    outputs = _apply_interrogative_upspeak(inputs, False)
    # Test
    assert expected == outputs
