import numpy as np
import pyworld as pw
from functools import lru_cache

from .MorphingQuery import MorphingQuery
from .MorphingPairParameter import MorphingPairParameter


@lru_cache(maxsize=4)
def create_morphing_pair_parameter(query: MorphingQuery) -> MorphingPairParameter:
    # FIXME: synthesis from anywhere (singleton engine)
    base_wave = engine.synthesis(query=query, speaker_id=query.base_speaker).astype(
        "float"
    )
    target_wave = engine.synthesis(query=query, speaker_id=query.target_speaker).astype(
        "float"
    )

    frame_period = 1.0
    fs = query.outputSamplingRate
    base_f0, base_time_axis = pw.harvest(base_wave, fs, frame_period=frame_period)
    base_spectrogram = pw.cheaptrick(base_wave, base_f0, base_time_axis, fs)
    base_aperiodicity = pw.d4c(base_wave, base_f0, base_time_axis, fs)

    target_f0, morph_time_axis = pw.harvest(
        target_wave, fs, frame_period=frame_period
    )
    target_spectrogram = pw.cheaptrick(target_wave, target_f0, morph_time_axis, fs)
    target_spectrogram.resize(base_spectrogram.shape)

    return MorphingPairParameter(
        fs,
        frame_period,
        base_f0,
        base_aperiodicity,
        base_spectrogram,
        target_spectrogram,
    )
