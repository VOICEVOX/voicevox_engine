from dataclasses import dataclass
from functools import lru_cache

import numpy as np
import pyworld as pw
from pydantic import BaseModel, Field

from ..model import AudioQuery
from ..synthesis_engine import SynthesisEngine


class MorphingException(Exception):
    def __init__(self, message: str):
        self.message = message


class MorphingQuery(BaseModel):
    audio_query: AudioQuery = Field(title="音声合成用のクエリ")
    base_speaker: int = Field(title="ベース話者")
    target_speaker: int = Field(title="ターゲット話者")
    morph_rate: float = Field(title="ベース話者の割合", ge=0.0, le=1.0)


# FIXME: ndarray type hint, https://github.com/JeremyCCHsu/Python-Wrapper-for-World-Vocoder/blob/2b64f86197573497c685c785c6e0e743f407b63e/pyworld/pyworld.pyx#L398  # noqa
@dataclass(frozen=True)
class MorphingPairParameter:
    fs: float
    frame_period: float
    base_f0: np.ndarray
    base_aperiodicity: np.ndarray
    base_spectrogram: np.ndarray
    target_spectrogram: np.ndarray


@dataclass(frozen=True)
class MorphingResult:
    query: MorphingQuery

    generated: np.ndarray


@lru_cache(maxsize=4)
def create_morphing_pair_parameter(
    engine: SynthesisEngine, query: MorphingQuery
) -> MorphingPairParameter:
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

    target_f0, morph_time_axis = pw.harvest(target_wave, fs, frame_period=frame_period)
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


def morphing(query: MorphingQuery) -> MorphingResult:
    """
    指定された2人の話者で音声を合成、指定した割合でモーフィングした音声を得ます。
    モーフィングの割合は`morph_rate`で指定でき、0.0でベースの話者、1.0でターゲットの話者に近づきます。
    """

    if query.morph_rate < 0.0 or query.morph_rate > 1.0:
        raise MorphingException("morph_rateは0.0から1.0の範囲で指定してください")

    # WORLDに掛けるため合成はモノラルで行う
    output_stereo = query.outputStereo
    query.outputStereo = False

    morph_param = create_morphing_pair_parameter(
        query.audio_query, query.base_speaker, query.target_speaker
    )

    # スペクトルの重み付き結合
    morph_spectrogram = (
        morph_param.base_spectrogram * (1.0 - query.morph_rate)
        + morph_param.target_spectrogram * query.morph_rate
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

    return MorphingResult(
        query=query,
        generated=y_h,
    )
