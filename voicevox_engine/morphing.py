"""
WORLDを使ってモーフィングするためのモジュール。
pyworldの入出力はnp.doubleやnp.float64なので注意。
"""

from copy import deepcopy
from dataclasses import dataclass
from itertools import chain

import numpy as np
import pyworld as pw
from numpy.typing import NDArray
from pydantic import BaseModel, Field
from soxr import resample

from .core.core_adapter import CoreAdapter
from .metas.Metas import Speaker, SpeakerSupportPermittedSynthesisMorphing, StyleId
from .model import AudioQuery, StyleIdNotFoundError
from .tts_pipeline.tts_engine import TTSEngine


class MorphableTargetInfo(BaseModel):
    is_morphable: bool = Field(title="指定した話者に対してモーフィングの可否")
    # FIXME: add reason property
    # reason: str | None = Field(title="is_morphableがfalseである場合、その理由")


@dataclass(frozen=True)
class _MorphingParameter:
    fs: int
    frame_period: float
    base_f0: NDArray[np.float64]
    base_aperiodicity: NDArray[np.float64]
    base_spectrogram: NDArray[np.float64]
    target_spectrogram: NDArray[np.float64]


def get_morphable_targets(
    speakers: list[Speaker],
    base_style_ids: list[StyleId],
) -> list[dict[StyleId, MorphableTargetInfo]]:
    """
    モーフィング可能一覧を生成する。
    指定されたベースキャラクターそれぞれに対し、引数のキャラクターリスト全体をチェックする。
    """
    morphable_targets_arr = []
    for base_style_id in base_style_ids:
        morphable_targets: dict[StyleId, MorphableTargetInfo] = {}
        for style in chain.from_iterable(speaker.styles for speaker in speakers):
            morphable_targets[style.id] = MorphableTargetInfo(
                is_morphable=is_morphable(speakers, base_style_id, style.id)
            )
        morphable_targets_arr.append(morphable_targets)

    return morphable_targets_arr


def is_morphable(
    speakers: list[Speaker], style_id_1: StyleId, style_id_2: StyleId
) -> bool:
    """スタイル ID で指定されたふたりのキャラクターがモーフィング可能か判定する。"""

    # スタイル ID にキャラクターを紐付ける対応表を生成する。
    style_id_to_character: dict[StyleId, Speaker] = {}
    for speaker in speakers:
        for style in speaker.styles:
            style_id_to_character[style.id] = speaker

    try:
        character_1 = style_id_to_character[style_id_1]
    except KeyError:
        raise StyleIdNotFoundError(style_id_1)
    try:
        character_2 = style_id_to_character[style_id_2]
    except KeyError:
        raise StyleIdNotFoundError(style_id_2)

    uuid_1 = character_1.speaker_uuid
    uuid_2 = character_2.speaker_uuid
    morphable_1 = character_1.supported_features.permitted_synthesis_morphing
    morphable_2 = character_2.supported_features.permitted_synthesis_morphing

    # 禁止されている場合はFalse
    if morphable_1 == SpeakerSupportPermittedSynthesisMorphing.NOTHING:
        return False
    elif morphable_2 == SpeakerSupportPermittedSynthesisMorphing.NOTHING:
        return False
    # 同一話者のみの場合は同一話者判定
    elif morphable_1 == SpeakerSupportPermittedSynthesisMorphing.SELF_ONLY:
        return uuid_1 == uuid_2
    elif morphable_2 == SpeakerSupportPermittedSynthesisMorphing.SELF_ONLY:
        return uuid_1 == uuid_2

    # 念のため許可されているかチェック
    return (
        morphable_1 == SpeakerSupportPermittedSynthesisMorphing.ALL
        and morphable_2 == SpeakerSupportPermittedSynthesisMorphing.ALL
    )


def synthesis_morphing_parameter(
    engine: TTSEngine,
    core: CoreAdapter,
    query: AudioQuery,
    base_style_id: StyleId,
    target_style_id: StyleId,
) -> _MorphingParameter:
    query = deepcopy(query)

    # 不具合回避のためデフォルトのサンプリングレートでWORLDに掛けた後に指定のサンプリングレートに変換する
    query.outputSamplingRate = core.default_sampling_rate

    # WORLDに掛けるため合成はモノラルで行う
    query.outputStereo = False

    base_wave = engine.synthesize_wave(query, base_style_id).astype(np.double)
    target_wave = engine.synthesize_wave(query, target_style_id).astype(np.double)

    fs = query.outputSamplingRate
    frame_period = 1.0
    base_f0, base_time_axis = pw.harvest(base_wave, fs, frame_period=frame_period)
    base_spectrogram = pw.cheaptrick(base_wave, base_f0, base_time_axis, fs)
    base_aperiodicity = pw.d4c(base_wave, base_f0, base_time_axis, fs)

    target_f0, morph_time_axis = pw.harvest(target_wave, fs, frame_period=frame_period)
    target_spectrogram = pw.cheaptrick(target_wave, target_f0, morph_time_axis, fs)
    target_spectrogram.resize(base_spectrogram.shape)

    return _MorphingParameter(
        fs=fs,
        frame_period=frame_period,
        base_f0=base_f0,
        base_aperiodicity=base_aperiodicity,
        base_spectrogram=base_spectrogram,
        target_spectrogram=target_spectrogram,
    )


def synthesis_morphing(
    morph_param: _MorphingParameter,
    morph_rate: float,
    output_fs: int,
    output_stereo: bool = False,
) -> NDArray[np.float32]:
    """
    指定した割合で、パラメータをもとにモーフィングした音声を生成します。

    Parameters
    ----------
    morph_param : MorphingParameter
        `synthesis_morphing_parameter`で作成したパラメータ

    morph_rate : float
        モーフィングの割合
        0.0でベースの音声、1.0でターゲットの音声に近づきます。

    Returns
    -------
    generated : NDArray[np.float32]
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

    _y_h: NDArray[np.float64] = pw.synthesize(
        morph_param.base_f0,
        morph_spectrogram,
        morph_param.base_aperiodicity,
        morph_param.fs,
        morph_param.frame_period,
    )
    y_h = _y_h.astype(np.float32)

    # TODO: tts_engine.py でのリサンプル処理と共通化する
    if output_fs != morph_param.fs:
        y_h = resample(y_h, morph_param.fs, output_fs)

    if output_stereo:
        y_h = np.array([y_h, y_h]).T

    return y_h
