import os
from typing import List, Optional

import numpy as np
import pyworld as pw
import snfa
from scipy.signal import resample
from snfa.viterbi import Segment

from ..model import AudioQuery

aligner: Optional[snfa.Aligner] = None


def _lazy_init(model_path: str):
    global aligner
    if aligner is None:
        if not os.path.exists(model_path):
            raise Exception("No model exists, check the build pipeline")
        aligner = snfa.Aligner(model_path)


def _query2phoneme(query: AudioQuery) -> List[str]:
    phoneme_list = []
    for accent_phrase in query.accent_phrases:
        for mora in accent_phrase.moras:
            if mora.consonant is not None:
                phoneme_list.append(mora.consonant)
            phoneme_list.append(mora.vowel)
        if accent_phrase.pause_mora:
            phoneme_list.append("pau")
    return ["pau"] + phoneme_list + ["pau"]


def _align(wav: np.ndarray, src_sr: int, query: AudioQuery):
    if len(wav.shape) == 2:
        wav = np.sum(wav, axis=1) / 2
    wav = resample(wav, aligner.sr * wav.shape[0] // src_sr)
    ph = _query2phoneme(query)
    segments, *_ = aligner(wav, ph, use_sec=False)

    return segments


def _norm_pitch(segments: List[Segment], pitch: np.ndarray):
    dur_length = sum([seg.length for seg in segments])
    scale_factor = pitch.shape[0] / dur_length
    normed_pitch = []
    for seg in segments:
        normed_pitch.append(
            np.average(
                pitch[int(seg.start * scale_factor) : int(seg.end * scale_factor)]
            )
        )
    return np.array(normed_pitch)


def _seg2time(segments: List[Segment]):
    duration = np.array([seg.length for seg in segments])
    return duration * aligner.hop_size / aligner.sr


def _guard_long_vowel(segments: List[Segment]):
    """
    `snfa` tends to collapse long vowels like `そう` and `どう`
    by giving more duration to the latter one and too little for the former.
    This function detects long vowels and gives 1/2 of
    latter one's duration to its former neighbour.
    """
    seg_idx = 0
    while seg_idx < len(segments) - 1:
        if (
            segments[seg_idx].label == segments[seg_idx].label
            and segments[seg_idx].length < 2
        ):
            mid_point = (segments[seg_idx].start + segments[seg_idx + 1].end) // 2
            segments[seg_idx].end = mid_point
            segments[seg_idx + 1].start = mid_point
            seg_idx += 2  # skip this long vowel
        else:
            seg_idx += 1
    return segments


def extract(wav: np.ndarray, src_sr: int, query: AudioQuery, model_path: str):
    _lazy_init(model_path)
    segments = _align(wav, src_sr, query)

    segments = _guard_long_vowel(segments)

    world_wav = wav.astype(np.double)
    pitch, _ = pw.harvest(world_wav, src_sr, frame_period=1.0)

    pitch = np.clip(np.log(pitch + 1e-5), 0, 6.5)  # 1e-5 to avoid log on zero

    normed_pit = _norm_pitch(segments, pitch)

    return _seg2time(segments)[1:-1], normed_pit[1:-1]
