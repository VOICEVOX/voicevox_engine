"""波形合成のテスト"""

import numpy as np

from voicevox_engine.model import AudioQuery
from voicevox_engine.tts_pipeline.model import AccentPhrase
from voicevox_engine.tts_pipeline.tts_engine import (
    _apply_intonation_scale,
    _apply_output_sampling_rate,
    _apply_output_stereo,
    _apply_pitch_scale,
    _apply_prepost_silence,
    _apply_speed_scale,
    _apply_volume_scale,
    _count_frame_per_unit,
    _query_to_decoder_feature,
    raw_wave_to_output_wave,
)

from .tts_utils import gen_mora, sec

TRUE_NUM_PHONEME = 45


def _gen_query(
    accent_phrases: list[AccentPhrase] | None = None,
    speedScale: float = 1.0,
    pitchScale: float = 1.0,
    intonationScale: float = 1.0,
    prePhonemeLength: float = 0.0,
    postPhonemeLength: float = 0.0,
    pauseLength: float | None = None,
    pauseLengthScale: float = 1.0,
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
        pauseLength=pauseLength,
        pauseLengthScale=pauseLengthScale,
        volumeScale=volumeScale,
        outputSamplingRate=outputSamplingRate,
        outputStereo=outputStereo,
    )


def test_apply_prepost_silence() -> None:
    """Test `_apply_prepost_silence()`."""
    # Inputs
    query = _gen_query(prePhonemeLength=sec(2), postPhonemeLength=sec(6))
    moras = [
        gen_mora("ヒ", "h", sec(2), "i", sec(4), 5.0),
    ]
    # Expects
    true_moras_with_silence = [
        gen_mora("　", None, None, "sil", sec(2), 0.0),
        gen_mora("ヒ", "h", sec(2), "i", sec(4), 5.0),
        gen_mora("　", None, None, "sil", sec(6), 0.0),
    ]
    # Outputs
    moras_with_silence = _apply_prepost_silence(moras, query)

    # Test
    assert moras_with_silence == true_moras_with_silence


def test_apply_speed_scale() -> None:
    """Test `_apply_speed_scale()`."""
    # Inputs
    query = _gen_query(speedScale=2.0)
    input_moras = [
        gen_mora("コ", "k", sec(2), "o", sec(4), 5.0),
        gen_mora("ン", None, None, "N", sec(4), 5.0),
        gen_mora("、", None, None, "pau", sec(2), 0.0),
        gen_mora("ヒ", "h", sec(2), "i", sec(4), 6.0),
        gen_mora("ホ", "h", sec(4), "O", sec(2), 0.0),
    ]
    # Expects - x2 fast
    true_moras = [
        gen_mora("コ", "k", sec(1), "o", sec(2), 5.0),
        gen_mora("ン", None, None, "N", sec(2), 5.0),
        gen_mora("、", None, None, "pau", sec(1), 0.0),
        gen_mora("ヒ", "h", sec(1), "i", sec(2), 6.0),
        gen_mora("ホ", "h", sec(2), "O", sec(1), 0.0),
    ]
    # Outputs
    moras = _apply_speed_scale(input_moras, query)

    # Test
    assert moras == true_moras


def test_apply_pitch_scale() -> None:
    """Test `_apply_pitch_scale()`."""
    # Inputs
    query = _gen_query(pitchScale=2.0)
    input_moras = [
        gen_mora("コ", "k", 0.0, "o", 0.0, 5.0),
        gen_mora("ン", None, None, "N", 0.0, 5.0),
        gen_mora("、", None, None, "pau", 0.0, 0.0),
        gen_mora("ヒ", "h", 0.0, "i", 0.0, 6.0),
        gen_mora("ホ", "h", 0.0, "O", 0.0, 0.0),
    ]
    # Expects - x4 value scaled
    true_moras = [
        gen_mora("コ", "k", 0.0, "o", 0.0, 20.0),
        gen_mora("ン", None, None, "N", 0.0, 20.0),
        gen_mora("、", None, None, "pau", 0.0, 0.0),
        gen_mora("ヒ", "h", 0.0, "i", 0.0, 24.0),
        gen_mora("ホ", "h", 0.0, "O", 0.0, 0.0),
    ]
    # Outputs
    moras = _apply_pitch_scale(input_moras, query)

    # Test
    assert moras == true_moras


def test_apply_intonation_scale() -> None:
    """Test `_apply_intonation_scale()`."""
    # Inputs
    query = _gen_query(intonationScale=0.5)
    input_moras = [
        gen_mora("コ", "k", 0.0, "o", 0.0, 5.0),
        gen_mora("ン", None, None, "N", 0.0, 5.0),
        gen_mora("、", None, None, "pau", 0.0, 0.0),
        gen_mora("ヒ", "h", 0.0, "i", 0.0, 8.0),
        gen_mora("ホ", "h", 0.0, "O", 0.0, 0.0),
    ]
    # Expects - mean=6 var x0.5 intonation scaling
    true_moras = [
        gen_mora("コ", "k", 0.0, "o", 0.0, 5.5),
        gen_mora("ン", None, None, "N", 0.0, 5.5),
        gen_mora("、", None, None, "pau", 0.0, 0.0),
        gen_mora("ヒ", "h", 0.0, "i", 0.0, 7.0),
        gen_mora("ホ", "h", 0.0, "O", 0.0, 0.0),
    ]
    # Outputs
    moras = _apply_intonation_scale(input_moras, query)

    # Test
    assert moras == true_moras


def test_apply_volume_scale() -> None:
    """Test `_apply_volume_scale()`."""
    # Inputs
    query = _gen_query(volumeScale=3.0)
    input_wave = np.array([0.0, 1.0, 2.0])
    # Expects - x3 scale
    true_wave = np.array([0.0, 3.0, 6.0])
    # Outputs
    wave = _apply_volume_scale(input_wave, query)

    # Test
    assert np.allclose(wave, true_wave)


def test_apply_output_sampling_rate() -> None:
    """Test `_apply_output_sampling_rate()`."""
    # Inputs
    query = _gen_query(outputSamplingRate=12000)
    input_wave = np.array([1.0 for _ in range(120)])
    input_sr_wave = 24000
    # Expects - half sampling rate
    true_wave = np.array([1.0 for _ in range(60)])
    assert true_wave.shape == (60,), "Prerequisites"
    # Outputs
    wave = _apply_output_sampling_rate(input_wave, input_sr_wave, query)

    # Test
    assert wave.shape[0] == true_wave.shape[0]


def test_apply_output_stereo() -> None:
    """Test `_apply_output_stereo()`."""
    # Inputs
    query = _gen_query(outputStereo=True)
    input_wave = np.array([1.0, 0.0, 2.0])
    # Expects - Stereo :: (Time, Channel)
    true_wave = np.array([[1.0, 1.0], [0.0, 0.0], [2.0, 2.0]])
    # Outputs
    wave = _apply_output_stereo(input_wave, query)

    # Test
    assert np.array_equal(wave, true_wave)


def test_count_frame_per_unit() -> None:
    """Test `_count_frame_per_unit()`."""
    # Inputs
    moras = [
        gen_mora("　", None, None, "　", sec(2), 0.0),
        gen_mora("コ", "k", sec(2), "o", sec(4), 0.0),
        gen_mora("ン", None, None, "N", sec(4), 0.0),
        gen_mora("、", None, None, "pau", sec(2), 0.0),
        gen_mora("ヒ", "h", sec(2), "i", sec(4), 0.0),
        gen_mora("ホ", "h", sec(4), "O", sec(2), 0.0),
        gen_mora("　", None, None, "　", sec(6), 0.0),
    ]

    # Expects
    #                             Pre k  o  N pau h  i  h  O Pst
    true_frame_per_phoneme_list = [2, 2, 4, 4, 2, 2, 4, 4, 2, 6]
    true_frame_per_phoneme = np.array(true_frame_per_phoneme_list, dtype=np.int32)
    #                         Pre ko  N pau hi hO Pst
    true_frame_per_mora_list = [2, 6, 4, 2, 6, 6, 6]
    true_frame_per_mora = np.array(true_frame_per_mora_list, dtype=np.int32)

    # Outputs
    frame_per_phoneme, frame_per_mora = _count_frame_per_unit(moras)

    # Test
    assert np.array_equal(frame_per_phoneme, true_frame_per_phoneme)
    assert np.array_equal(frame_per_mora, true_frame_per_mora)


def test_query_to_decoder_feature() -> None:
    """Test `_query_to_decoder_feature()`."""
    # Inputs
    accent_phrases = [
        AccentPhrase(
            moras=[
                gen_mora("コ", "k", sec(2), "o", sec(4), 5.0),
                gen_mora("ン", None, None, "N", sec(4), 5.0),
            ],
            accent=1,
            pause_mora=gen_mora("、", None, None, "pau", sec(2), 0.0),
        ),
        AccentPhrase(
            moras=[
                gen_mora("ヒ", "h", sec(2), "i", sec(4), 8.0),
                gen_mora("ホ", "h", sec(4), "O", sec(2), 0.0),
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
        prePhonemeLength=sec(2),
        postPhonemeLength=sec(6),
        pauseLength=sec(16),
        pauseLengthScale=0.25,
    )

    # Expects
    # frame_per_phoneme
    #                        Pre k  o  N pau h  i  h  O Pst
    true_frame_per_phoneme = [1, 1, 2, 2, 2, 1, 2, 2, 1, 3]
    n_frame = sum(true_frame_per_phoneme)
    # phoneme
    #                     Pr  k   o   o  N  N pau pau h   i   i   h   h  O Pt Pt Pt
    frame_phoneme_idxs = [0, 23, 30, 30, 4, 4, 0, 0, 19, 21, 21, 19, 19, 5, 0, 0, 0]
    true_phoneme = np.zeros([n_frame, TRUE_NUM_PHONEME], dtype=np.float32)
    for frame_idx, phoneme_idx in enumerate(frame_phoneme_idxs):
        true_phoneme[frame_idx, phoneme_idx] = 1.0
    # Pitch
    #                   paw ko  N pau hi hO paw
    # frame_per_vowel = [1, 3,  2, 1, 3, 3, 3]
    #           pau   ko    ko    ko     N     N
    true1_f0 = [0.0, 22.0, 22.0, 22.0, 22.0, 22.0]
    #           pau  pau  hi    hi    hi
    true2_f0 = [0.0, 0.0, 28.0, 28.0, 28.0]
    #           hO   hO   hO   paw  paw  paw
    true3_f0 = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    true_f0 = np.array(true1_f0 + true2_f0 + true3_f0, dtype=np.float32)

    # Outputs
    phoneme, f0 = _query_to_decoder_feature(query)

    # Test
    assert np.array_equal(phoneme, true_phoneme)
    assert np.array_equal(f0, true_f0)


def test_raw_wave_to_output_wave_with_resample() -> None:
    """Test `raw_wave_to_output_wave` with resampling option."""
    # Inputs
    query = _gen_query(volumeScale=2, outputSamplingRate=48000, outputStereo=True)
    raw_wave = np.random.rand(240).astype(np.float32)
    sr_raw_wave = 24000

    # Expects
    true_wave_shape = (480, 2)

    # Outputs
    wave = raw_wave_to_output_wave(query, raw_wave, sr_raw_wave)

    assert wave.shape == true_wave_shape


def test_raw_wave_to_output_wave_without_resample() -> None:
    """Test `raw_wave_to_output_wave`  without resampling option."""
    # Inputs
    query = _gen_query(volumeScale=2, outputStereo=True)
    raw_wave = np.random.rand(240).astype(np.float32)
    sr_raw_wave = 24000

    # Expects
    true_wave = np.array([2 * raw_wave, 2 * raw_wave]).T

    # Outputs
    wave = raw_wave_to_output_wave(query, raw_wave, sr_raw_wave)

    assert np.allclose(wave, true_wave)
