"""音符単位の音高補正"""

import numpy as np
from numpy.typing import NDArray
from scipy.ndimage import gaussian_filter1d
from scipy.signal import savgol_filter
from scipy.signal.windows import tukey

from .phoneme import Phoneme

DEFAULT_CORRECT_F0_ALPHA = 0.5

_FRAME_RATE = 24000 / 256
_VOWEL_IDS = [Phoneme(symbol).id for symbol in "aiueoAIUEON"]
_PAUSE_ID = Phoneme("pau").id


def correct_pitch(
    f0: NDArray[np.float32],
    frame_phonemes: NDArray[np.int64],
    frame_keys: NDArray[np.int64],
    note_lengths: NDArray[np.int64],
    consonant_lengths: NDArray[np.int64],
    *,
    tukey_alpha: float = DEFAULT_CORRECT_F0_ALPHA,
) -> NDArray[np.float32]:
    """
    母音から推定した音高と楽譜の差を使い、音符ごとに F0 [Hz] を補正する。

    f0 は base_f0 で Hz に戻して平滑化した予測値を渡す。
    frame_phonemes と frame_keys は f0 と同じ長さとし、休符のキーは -1 とする。
    note_lengths は楽譜上の音符長、consonant_lengths は音素長の計算で調整された子音長とする。
    """
    voiced = (frame_keys >= 0) & (frame_phonemes != _PAUSE_ID) & (f0 > 0)
    vowels = voiced & np.isin(frame_phonemes, _VOWEL_IDS)
    if not np.any(vowels):
        return f0

    midi = np.zeros(len(f0))
    midi[voiced] = 69 + 12 * np.log2(f0[voiced].astype(np.float64) / 440)
    correction = np.zeros(len(f0))
    # 子音は楽譜上のノート開始より前に配置される。実際の音素列に境界を合わせる。
    starts = np.r_[0, np.cumsum(note_lengths)[:-1] - consonant_lengths[1:], len(f0)]
    for start, end in zip(starts[:-1], starts[1:], strict=True):
        span = slice(start, end)
        if not np.any(vowels[span]):
            continue

        error = midi[span] - frame_keys[start]
        # 音符の中央と、目標音高に近い母音を重く扱う（ガウスの σ は 0.5 半音）。
        weights = tukey(len(error), alpha=tukey_alpha) * vowels[span]
        weights *= np.exp(-0.5 * (error / 0.5) ** 2)
        if len(error) >= 5:
            # 55 ms 相当の 5 フレームで平滑化し、残差が大きいフレームを軽くする。
            residual = error - savgol_filter(error, 5, 3)
            weights /= np.minimum(1 + 27 * np.abs(residual), 15)
        if weights.sum() > 0:
            correction[span] = -np.average(error, weights=weights)

    # 音符間の補正量を滑らかにつなぎ、半音差を Hz の倍率に戻す。
    correction = gaussian_filter1d(correction, sigma=0.030 * _FRAME_RATE)
    corrected = f0.copy()
    corrected[voiced] *= np.exp2(correction[voiced] / 12)
    return corrected
