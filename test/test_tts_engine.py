from typing import Union
from unittest import TestCase
from unittest.mock import Mock

import numpy

from voicevox_engine.metas.Metas import StyleId
from voicevox_engine.model import AccentPhrase, AudioQuery, Mora
from voicevox_engine.tts_pipeline import TTSEngine
from voicevox_engine.tts_pipeline.acoustic_feature_extractor import Phoneme
from voicevox_engine.tts_pipeline.tts_engine import (
    apply_intonation_scale,
    apply_output_sampling_rate,
    apply_output_stereo,
    apply_pitch_scale,
    apply_prepost_silence,
    apply_speed_scale,
    apply_volume_scale,
    count_frame_per_unit,
    pre_process,
    query_to_decoder_feature,
    raw_wave_to_output_wave,
    split_mora,
    to_flatten_moras,
    to_flatten_phonemes,
    unvoiced_mora_phoneme_list,
)

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


def _gen_query(
    accent_phrases: list[AccentPhrase] | None = None,
    speedScale: float = 1.0,
    pitchScale: float = 1.0,
    intonationScale: float = 1.0,
    prePhonemeLength: float = 0.0,
    postPhonemeLength: float = 0.0,
    volumeScale: float = 1.0,
    outputSamplingRate: int = 24000,
    outputStereo: bool = False,
) -> AudioQuery:
    """Generate AudioQuery with default meaningless arguments for test simplicity."""
    accent_phrases = [] if accent_phrases is None else accent_phrases
    return AudioQuery(
        accent_phrases=accent_phrases,
        speedScale=speedScale,
        pitchScale=pitchScale,
        intonationScale=intonationScale,
        prePhonemeLength=prePhonemeLength,
        postPhonemeLength=postPhonemeLength,
        volumeScale=volumeScale,
        outputSamplingRate=outputSamplingRate,
        outputStereo=outputStereo,
    )


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


def test_apply_prepost_silence():
    """Test `apply_prepost_silence`."""
    # Inputs
    query = _gen_query(prePhonemeLength=2 * 0.01067, postPhonemeLength=6 * 0.01067)
    moras = [
        _gen_mora("ヒ", "h", 2 * 0.01067, "i", 4 * 0.01067, 100.0),
    ]

    # Expects
    true_moras_with_silence = [
        _gen_mora("　", None, None, "sil", 2 * 0.01067, 0.0),
        _gen_mora("ヒ", "h", 2 * 0.01067, "i", 4 * 0.01067, 100.0),
        _gen_mora("　", None, None, "sil", 6 * 0.01067, 0.0),
    ]

    # Outputs
    moras_with_silence = apply_prepost_silence(moras, query)

    assert moras_with_silence == true_moras_with_silence


def test_apply_speed_scale():
    """Test `apply_speed_scale`."""
    # Inputs
    query = _gen_query(speedScale=2.0)
    input_moras = [
        _gen_mora("コ", "k", 2 * 0.01067, "o", 4 * 0.01067, 50.0),
        _gen_mora("ン", None, None, "N", 4 * 0.01067, 50.0),
        _gen_mora("、", None, None, "pau", 2 * 0.01067, 0.0),
        _gen_mora("ヒ", "h", 2 * 0.01067, "i", 4 * 0.01067, 125.0),
        _gen_mora("ホ", "h", 4 * 0.01067, "O", 2 * 0.01067, 0.0),
    ]

    # Expects - x2 fast
    true_moras = [
        _gen_mora("コ", "k", 1 * 0.01067, "o", 2 * 0.01067, 50.0),
        _gen_mora("ン", None, None, "N", 2 * 0.01067, 50.0),
        _gen_mora("、", None, None, "pau", 1 * 0.01067, 0.0),
        _gen_mora("ヒ", "h", 1 * 0.01067, "i", 2 * 0.01067, 125.0),
        _gen_mora("ホ", "h", 2 * 0.01067, "O", 1 * 0.01067, 0.0),
    ]

    # Outputs
    moras = apply_speed_scale(input_moras, query)

    assert moras == true_moras


def test_apply_pitch_scale():
    """Test `apply_pitch_scale`."""
    # Inputs
    query = _gen_query(pitchScale=2.0)
    input_moras = [
        _gen_mora("コ", "k", 0.0, "o", 0.0, 50.0),
        _gen_mora("ン", None, None, "N", 0.0, 50.0),
        _gen_mora("、", None, None, "pau", 0.0, 0.0),
        _gen_mora("ヒ", "h", 0.0, "i", 0.0, 125.0),
        _gen_mora("ホ", "h", 0.0, "O", 0.0, 0.0),
    ]

    # Expects - x4 value scaled
    true_moras = [
        _gen_mora("コ", "k", 0.0, "o", 0.0, 200.0),
        _gen_mora("ン", None, None, "N", 0.0, 200.0),
        _gen_mora("、", None, None, "pau", 0.0, 0.0),
        _gen_mora("ヒ", "h", 0.0, "i", 0.0, 500.0),
        _gen_mora("ホ", "h", 0.0, "O", 0.0, 0.0),
    ]

    # Outputs
    moras = apply_pitch_scale(input_moras, query)

    assert moras == true_moras


def test_apply_intonation_scale():
    """Test `apply_intonation_scale`."""
    # Inputs
    query = _gen_query(intonationScale=0.5)
    input_moras = [
        _gen_mora("コ", "k", 0.0, "o", 0.0, 200.0),
        _gen_mora("ン", None, None, "N", 0.0, 200.0),
        _gen_mora("、", None, None, "pau", 0.0, 0.0),
        _gen_mora("ヒ", "h", 0.0, "i", 0.0, 500.0),
        _gen_mora("ホ", "h", 0.0, "O", 0.0, 0.0),
    ]

    # Expects - mean=300 var x0.5 intonation scaling
    true_moras = [
        _gen_mora("コ", "k", 0.0, "o", 0.0, 250.0),
        _gen_mora("ン", None, None, "N", 0.0, 250.0),
        _gen_mora("、", None, None, "pau", 0.0, 0.0),
        _gen_mora("ヒ", "h", 0.0, "i", 0.0, 400.0),
        _gen_mora("ホ", "h", 0.0, "O", 0.0, 0.0),
    ]

    # Outputs
    moras = apply_intonation_scale(input_moras, query)

    assert moras == true_moras


def test_apply_volume_scale():
    """Test `apply_volume_scale`."""
    # Inputs
    query = _gen_query(volumeScale=3.0)
    input_wave = numpy.array([0.0, 1.0, 2.0])

    # Expects - x3 scale
    true_wave = numpy.array([0.0, 3.0, 6.0])

    # Outputs
    wave = apply_volume_scale(input_wave, query)

    assert numpy.allclose(wave, true_wave)


def test_apply_output_sampling_rate():
    """Test `apply_output_sampling_rate`."""
    # Inputs
    query = _gen_query(outputSamplingRate=12000)
    input_wave = numpy.array([1.0 for _ in range(120)])
    input_sr_wave = 24000

    # Expects - half sampling rate
    true_wave = numpy.array([1.0 for _ in range(60)])
    assert true_wave.shape == (60,), "Prerequisites"

    # Outputs
    wave = apply_output_sampling_rate(input_wave, input_sr_wave, query)

    assert wave.shape[0] == true_wave.shape[0]


def test_apply_output_stereo():
    """Test `apply_output_stereo`."""
    # Inputs
    query = _gen_query(outputStereo=True)
    input_wave = numpy.array([1.0, 0.0, 2.0])

    # Expects - Stereo :: (Time, Channel)
    true_wave = numpy.array([[1.0, 1.0], [0.0, 0.0], [2.0, 2.0]])

    # Outputs
    wave = apply_output_stereo(input_wave, query)

    assert numpy.array_equal(wave, true_wave)


def test_count_frame_per_unit():
    """Test `count_frame_per_unit`."""
    # Inputs
    moras = [
        _gen_mora("　", None, None, "　", 2 * 0.01067, 0.0),  # 0.01067 [sec/frame]
        _gen_mora("コ", "k", 2 * 0.01067, "o", 4 * 0.01067, 0.0),
        _gen_mora("ン", None, None, "N", 4 * 0.01067, 0.0),
        _gen_mora("、", None, None, "pau", 2 * 0.01067, 0.0),
        _gen_mora("ヒ", "h", 2 * 0.01067, "i", 4 * 0.01067, 0.0),
        _gen_mora("ホ", "h", 4 * 0.01067, "O", 2 * 0.01067, 0.0),
        _gen_mora("　", None, None, "　", 6 * 0.01067, 0.0),
    ]

    # Expects
    #                             Pre k  o  N pau h  i  h  O Pst
    true_frame_per_phoneme_list = [2, 2, 4, 4, 2, 2, 4, 4, 2, 6]
    true_frame_per_phoneme = numpy.array(true_frame_per_phoneme_list, dtype=numpy.int32)
    #                         Pre ko  N pau hi hO Pst
    true_frame_per_mora_list = [2, 6, 4, 2, 6, 6, 6]
    true_frame_per_mora = numpy.array(true_frame_per_mora_list, dtype=numpy.int32)

    # Outputs
    frame_per_phoneme, frame_per_mora = count_frame_per_unit(moras)

    assert numpy.array_equal(frame_per_phoneme, true_frame_per_phoneme)
    assert numpy.array_equal(frame_per_mora, true_frame_per_mora)


def test_query_to_decoder_feature():
    """Test `query_to_decoder_feature`."""
    # Inputs
    accent_phrases = [
        AccentPhrase(
            moras=[
                _gen_mora("コ", "k", 2 * 0.01067, "o", 4 * 0.01067, 50.0),
                _gen_mora("ン", None, None, "N", 4 * 0.01067, 50.0),
            ],
            accent=1,
            pause_mora=_gen_mora("、", None, None, "pau", 2 * 0.01067, 0.0),
        ),
        AccentPhrase(
            moras=[
                _gen_mora("ヒ", "h", 2 * 0.01067, "i", 4 * 0.01067, 125.0),
                _gen_mora("ホ", "h", 4 * 0.01067, "O", 2 * 0.01067, 0.0),
            ],
            accent=1,
            pause_mora=None,
        ),
    ]
    query = _gen_query(
        accent_phrases=accent_phrases,
        speedScale=2.0,
        pitchScale=2.0,
        intonationScale=0.5,
        prePhonemeLength=2 * 0.01067,
        postPhonemeLength=6 * 0.01067,
    )

    # Expects
    # frame_per_phoneme
    #                        Pre k  o  N pau h  i  h  O Pst
    true_frame_per_phoneme = [1, 1, 2, 2, 1, 1, 2, 2, 1, 3]
    n_frame = sum(true_frame_per_phoneme)
    # phoneme
    #                     Pr  k   o   o  N  N pau  h   i   i   h   h  O Pt Pt Pt
    frame_phoneme_idxs = [0, 23, 30, 30, 4, 4, 0, 19, 21, 21, 19, 19, 5, 0, 0, 0]
    true_phoneme = numpy.zeros([n_frame, TRUE_NUM_PHONEME], dtype=numpy.float32)
    for frame_idx, phoneme_idx in enumerate(frame_phoneme_idxs):
        true_phoneme[frame_idx, phoneme_idx] = 1.0
    # Pitch
    #                   paw ko  N pau hi hO paw
    # frame_per_vowel = [1, 3,  2, 1, 3, 3, 3]
    #           pau   ko     ko     ko      N      N
    true1_f0 = [0.0, 250.0, 250.0, 250.0, 250.0, 250.0]
    #           pau   hi     hi     hi
    true2_f0 = [0.0, 400.0, 400.0, 400.0]
    #           hO   hO   hO   paw  paw  paw
    true3_f0 = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    true_f0 = numpy.array(true1_f0 + true2_f0 + true3_f0, dtype=numpy.float32)

    # Outputs
    phoneme, f0 = query_to_decoder_feature(query)

    assert numpy.array_equal(phoneme, true_phoneme)
    assert numpy.array_equal(f0, true_f0)


def test_raw_wave_to_output_wave_with_resample():
    """Test `raw_wave_to_output_wave` with resampling option."""
    # Inputs
    query = _gen_query(volumeScale=2, outputSamplingRate=48000, outputStereo=True)
    raw_wave = numpy.random.rand(240)
    sr_raw_wave = 24000

    # Expects
    true_wave_shape = (480, 2)

    # Outputs
    wave = raw_wave_to_output_wave(query, raw_wave, sr_raw_wave)

    assert wave.shape == true_wave_shape


def test_raw_wave_to_output_wave_without_resample():
    """Test `raw_wave_to_output_wave`  without resampling option."""
    # Inputs
    query = _gen_query(volumeScale=2, outputStereo=True)
    raw_wave = numpy.random.rand(240)
    sr_raw_wave = 24000

    # Expects
    true_wave = numpy.array([2 * raw_wave, 2 * raw_wave]).T

    # Outputs
    wave = raw_wave_to_output_wave(query, raw_wave, sr_raw_wave)

    assert numpy.allclose(wave, true_wave)


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


def is_same_ojt_phoneme_list(
    p1s: list[Phoneme | None] | list[Phoneme], p2s: list[Phoneme | None] | list[Phoneme]
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


def test_split_mora(self):
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
    self.assertTrue(is_same_ojt_phoneme_list(vowels, true_vowels))
    self.assertTrue(is_same_ojt_phoneme_list(consonants, true_consonants))


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

    def test_pre_process(self):
        flatten_moras, phoneme_data_list = pre_process(_gen_hello_hiho_accent_phrases())

        mora_index = 0
        phoneme_index = 1

        self.assertTrue(is_same_phoneme(phoneme_data_list[0], Phoneme("pau")))
        for accent_phrase in _gen_hello_hiho_accent_phrases():
            moras = accent_phrase.moras
            for mora in moras:
                self.assertEqual(flatten_moras[mora_index], mora)
                mora_index += 1
                if mora.consonant is not None:
                    self.assertTrue(
                        is_same_phoneme(
                            phoneme_data_list[phoneme_index], Phoneme(mora.consonant)
                        )
                    )
                    phoneme_index += 1
                self.assertTrue(
                    is_same_phoneme(
                        phoneme_data_list[phoneme_index], Phoneme(mora.vowel)
                    )
                )
                phoneme_index += 1
            if accent_phrase.pause_mora:
                self.assertEqual(flatten_moras[mora_index], accent_phrase.pause_mora)
                mora_index += 1
                self.assertTrue(
                    is_same_phoneme(phoneme_data_list[phoneme_index], Phoneme("pau"))
                )
                phoneme_index += 1
        self.assertTrue(
            is_same_phoneme(phoneme_data_list[phoneme_index], Phoneme("pau"))
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
            # unvoiced_mora_phoneme_listのPhoneme ID版
            unvoiced_mora_phoneme_id_list = [
                Phoneme(p).phoneme_id for p in unvoiced_mora_phoneme_list
            ]
            if vowel_phoneme_list[i] in unvoiced_mora_phoneme_id_list:
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
