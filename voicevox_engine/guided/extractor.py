import os
from typing import List, Optional

import numpy as np
import pyworld as pw
import snfa
from scipy.signal import resample

from ..model import AudioQuery

aligner: Optional[snfa.Aligner] = None
model_path = "cv_jp.bin"


def _lazy_init():
    global aligner
    if aligner is None:
        if not os.path.exists(model_path):
            raise Exception("No model exists, check the build pipeline")
        aligner = snfa.Aligner(model_path)


def query2phoneme(query: AudioQuery) -> List[str]:
    phoneme_list = []
    for accent_phrase in query.accent_phrases:
        for mora in accent_phrase.moras:
            if mora.consonant is not None:
                phoneme_list.append(mora.consonant)
            phoneme_list.append(mora.vowel)
        if accent_phrase.pause_mora:
            phoneme_list.append("pau")
    return ["pau"] + phoneme_list + ["pau"]


def align(wav: np.ndarray, src_sr: int, query: AudioQuery):
    _lazy_init()

    if len(wav.shape) == 2:
        wav = np.sum(wav, axis=1) / 2
    wav = resample(wav, aligner.sr * wav.shape[0] // src_sr)
    ph = query2phoneme(query)
    segments, *_ = aligner(wav, ph, use_sec=False)

    # scale to 24000hz
    resample_factor = src_sr / aligner.sr
    for seg in segments:
        seg.start = int(seg.start * resample_factor)
        seg.end = int(seg.end * resample_factor)

    return segments


def frame_to_time(dur: np.ndarray, src_sr: int):
    return dur * aligner.hop_size / src_sr


def extract(wav: np.ndarray, src_sr: int, query: AudioQuery):
    segments = align(wav, src_sr, query)

    world_wav = wav.astype(np.double)
    pitch, _ = pw.harvest(world_wav, src_sr, frame_period=1.0)

    duration = np.array([seg.length for seg in segments])
    length = np.sum(duration)

    pitch = np.clip(resample(pitch, length), 0, np.inf)
    pitch = np.clip(np.log(pitch + 1e-9), 0, 6.5)

    normed_pit = np.zeros_like(duration, dtype=np.float32)

    for idx, seg in enumerate(segments):
        normed_pit[idx] = np.average(pitch[seg.start : seg.end])

    return frame_to_time(duration, src_sr)[1:-1], normed_pit[1:-1]
