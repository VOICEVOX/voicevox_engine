import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pyworld as pw

from voicevox_engine.synthesis_engine.synthesis_engine_base import SynthesisEngineBase

from .model import AudioQuery, SpeakerSupportSynthesisMorphing
from .synthesis_engine import SynthesisEngine


# FIXME: ndarray type hint, https://github.com/JeremyCCHsu/Python-Wrapper-for-World-Vocoder/blob/2b64f86197573497c685c785c6e0e743f407b63e/pyworld/pyworld.pyx#L398  # noqa
@dataclass(frozen=True)
class MorphingParameter:
    fs: float
    frame_period: float
    base_f0: np.ndarray
    base_aperiodicity: np.ndarray
    base_spectrogram: np.ndarray
    target_spectrogram: np.ndarray


def create_morphing_parameter(
    base_wave: np.ndarray,
    target_wave: np.ndarray,
    fs: float,
) -> MorphingParameter:
    frame_period = 1.0
    base_f0, base_time_axis = pw.harvest(base_wave, fs, frame_period=frame_period)
    base_spectrogram = pw.cheaptrick(base_wave, base_f0, base_time_axis, fs)
    base_aperiodicity = pw.d4c(base_wave, base_f0, base_time_axis, fs)

    target_f0, morph_time_axis = pw.harvest(target_wave, fs, frame_period=frame_period)
    target_spectrogram = pw.cheaptrick(target_wave, target_f0, morph_time_axis, fs)
    target_spectrogram.resize(base_spectrogram.shape)

    return MorphingParameter(
        fs=fs,
        frame_period=frame_period,
        base_f0=base_f0,
        base_aperiodicity=base_aperiodicity,
        base_spectrogram=base_spectrogram,
        target_spectrogram=target_spectrogram,
    )


def is_synthesis_morphing_permitted(
    engine: SynthesisEngineBase, base_speaker: int, target_speaker: int
) -> Optional[bool]:
    """
    指定されたspeakerがモーフィング可能かどうか返す
    speakerが見つからない場合はNoneを返す
    """

    speakers = json.loads(engine.speakers)
    base_speaker_info, target_speaker_info = None, None
    for speaker in speakers:
        style_id_arr = tuple(map(lambda style: style["id"], speaker["styles"]))
        if base_speaker_info is None and base_speaker in style_id_arr:
            base_speaker_info = speaker
        if target_speaker_info is None and target_speaker in style_id_arr:
            target_speaker_info = speaker

    if base_speaker_info is None or target_speaker_info is None:
        return None

    base_speaker_morphing_info: SpeakerSupportSynthesisMorphing = base_speaker_info.get(
        "supported_features", dict()
    ).get("synthesis_morphing", SpeakerSupportSynthesisMorphing(None))

    target_speaker_morphing_info: SpeakerSupportSynthesisMorphing = (
        target_speaker_info.get("supported_features", dict()).get(
            "synthesis_morphing", SpeakerSupportSynthesisMorphing(None)
        )
    )

    if (
        base_speaker_morphing_info == SpeakerSupportSynthesisMorphing.PROHIBIT
        or target_speaker_morphing_info == SpeakerSupportSynthesisMorphing.PROHIBIT
    ):
        return False
    if (
        base_speaker_morphing_info == SpeakerSupportSynthesisMorphing.SELF_MORPHING_ONLY
        or target_speaker_morphing_info
        == SpeakerSupportSynthesisMorphing.SELF_MORPHING_ONLY
    ):
        return base_speaker_info["speaker_uuid"] == target_speaker_info["speaker_uuid"]
    return (
        base_speaker_morphing_info == SpeakerSupportSynthesisMorphing.PREMIT
        and target_speaker_morphing_info == SpeakerSupportSynthesisMorphing.PREMIT
    )


def synthesis_morphing_parameter(
    engine: SynthesisEngine,
    query: AudioQuery,
    base_speaker: int,
    target_speaker: int,
) -> MorphingParameter:
    query = deepcopy(query)

    # WORLDに掛けるため合成はモノラルで行う
    query.outputStereo = False

    base_wave = engine.synthesis(query=query, speaker_id=base_speaker).astype("float")
    target_wave = engine.synthesis(query=query, speaker_id=target_speaker).astype(
        "float"
    )

    return create_morphing_parameter(
        base_wave=base_wave,
        target_wave=target_wave,
        fs=query.outputSamplingRate,
    )


def synthesis_morphing(
    morph_param: MorphingParameter,
    morph_rate: float,
    output_stereo: bool = False,
) -> np.ndarray:
    """
    指定した割合で、パラメータをもとにモーフィングした音声を生成します。

    Parameters
    ----------
    morph_param : MorphingParameter
        `synthesis_morphing_parameter`または`create_morphing_parameter`で作成したパラメータ

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
