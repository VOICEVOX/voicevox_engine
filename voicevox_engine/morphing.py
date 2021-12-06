from copy import deepcopy
from dataclasses import dataclass

import numpy as np
import pyworld as pw

from .model import AudioQuery
from .synthesis_engine import SynthesisEngine


# FIXME: ndarray type hint, https://github.com/JeremyCCHsu/Python-Wrapper-for-World-Vocoder/blob/2b64f86197573497c685c785c6e0e743f407b63e/pyworld/pyworld.pyx#L398  # noqa
@dataclass(frozen=True)
class WorldParameters:
    fs: float
    frame_period: float
    base_f0: np.ndarray
    base_aperiodicity: np.ndarray
    base_spectrogram: np.ndarray
    target_spectrogram: np.ndarray


def create_world_parameters(
    base_wave: np.ndarray,
    target_wave: np.ndarray,
    fs: float,
) -> WorldParameters:
    frame_period = 1.0
    base_f0, base_time_axis = pw.harvest(base_wave, fs, frame_period=frame_period)
    base_spectrogram = pw.cheaptrick(base_wave, base_f0, base_time_axis, fs)
    base_aperiodicity = pw.d4c(base_wave, base_f0, base_time_axis, fs)

    target_f0, morph_time_axis = pw.harvest(target_wave, fs, frame_period=frame_period)
    target_spectrogram = pw.cheaptrick(target_wave, target_f0, morph_time_axis, fs)
    target_spectrogram.resize(base_spectrogram.shape)

    return WorldParameters(
        fs=fs,
        frame_period=frame_period,
        base_f0=base_f0,
        base_aperiodicity=base_aperiodicity,
        base_spectrogram=base_spectrogram,
        target_spectrogram=target_spectrogram,
    )


def synthesis_world_parameters(
    engine: SynthesisEngine,
    query: AudioQuery,
    base_speaker: int,
    target_speaker: int,
) -> WorldParameters:
    query = deepcopy(query)

    # WORLDに掛けるため合成はモノラルで行う
    query.outputStereo = False

    base_wave = engine.synthesis(query=query, speaker_id=base_speaker).astype("float")
    target_wave = engine.synthesis(query=query, speaker_id=target_speaker).astype(
        "float"
    )

    return create_world_parameters(
        base_wave=base_wave,
        target_wave=target_wave,
        fs=query.outputSamplingRate,
    )


def synthesis_world(
    morph_param: WorldParameters,
    morph_rate: float,
    output_stereo: bool = False,
) -> np.ndarray:
    """
    指定した割合で、パラメータをもとにモーフィングした音声を生成します。

    Parameters
    ----------
    morph_param : WorldParameters
        `synthesis_world_parameters`または`create_world_parameters`で作成したパラメータ

    morph_rate : float
        モーフィングの割合
        0.0でベースの話者、1.0でターゲットの話者に近づきます。

    Returns
    -------
    generated : np.ndarray
        モーフィングした音声

    Raises
    -------
    ValueError
        morph_rate ∈ [0, 1]
    """

    if morph_rate < 0.0 or morph_rate > 1.0:
        raise ValueError("morph_rateは0.0から1.0の範囲で指定してください")

    morph_spectrogram = (
        morph_param.base_spectrogram * (1.0 - morph_rate)
        + morph_param.target_spectrogram * morph_rate
    )

    y_h = pw.synthesize(
        morph_param.base_f0,
        morph_spectrogram,
        morph_param.base_aperiodicity,
        morph_param.fs,
        morph_param.frame_period,
    )

    if output_stereo:
        y_h = np.array([y_h, y_h]).T

    return y_h
