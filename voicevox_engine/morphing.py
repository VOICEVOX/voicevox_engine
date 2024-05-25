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
from soxr import resample

from .core.core_adapter import CoreAdapter
from .metas.Metas import Speaker, SpeakerSupportPermittedSynthesisMorphing, StyleId
from .model import AudioQuery, MorphableTargetInfo, StyleIdNotFoundError
from .tts_pipeline.tts_engine import TTSEngine


@dataclass(frozen=True)
class MorphingParameter:
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
                is_morphable=is_synthesis_morphing_permitted(
                    speakers,
                    base_style_id=base_style_id,
                    target_style_id=style.id,
                )
            )
        morphable_targets_arr.append(morphable_targets)

    return morphable_targets_arr


def construct_lookup(speakers: list[Speaker]) -> dict[StyleId, Speaker]:
    """スタイル ID にキャラクターを紐付ける対応表を生成する。"""
    lookup_table: dict[StyleId, Speaker] = {}
    for speaker in speakers:
        for style in speaker.styles:
            lookup_table[style.id] = speaker
    return lookup_table


def is_synthesis_morphing_permitted(
    speakers: list[Speaker], base_style_id: StyleId, target_style_id: StyleId
) -> bool:
    """base キャラクターと target キャラクターをモーフィング可能か判定する。"""
    speaker_lookup = construct_lookup(speakers)
    try:
        base = speaker_lookup[base_style_id]
    except KeyError:
        raise StyleIdNotFoundError(base_style_id)
    try:
        target = speaker_lookup[target_style_id]
    except KeyError:
        raise StyleIdNotFoundError(target_style_id)

    base_uuid = base.speaker_uuid
    target_uuid = target.speaker_uuid
    base_morphable = base.supported_features.permitted_synthesis_morphing
    target_morphable = target.supported_features.permitted_synthesis_morphing

    # 禁止されている場合はFalse
    if base_morphable == SpeakerSupportPermittedSynthesisMorphing.NOTHING:
        return False
    elif target_morphable == SpeakerSupportPermittedSynthesisMorphing.NOTHING:
        return False
    # 同一話者のみの場合は同一話者判定
    elif base_morphable == SpeakerSupportPermittedSynthesisMorphing.SELF_ONLY:
        return base_uuid == target_uuid
    elif target_morphable == SpeakerSupportPermittedSynthesisMorphing.SELF_ONLY:
        return base_uuid == target_uuid

    # 念のため許可されているかチェック
    return (
        base_morphable == SpeakerSupportPermittedSynthesisMorphing.ALL
        and target_morphable == SpeakerSupportPermittedSynthesisMorphing.ALL
    )


def synthesis_morphing_parameter(
    engine: TTSEngine,
    core: CoreAdapter,
    query: AudioQuery,
    base_style_id: StyleId,
    target_style_id: StyleId,
) -> MorphingParameter:
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

    return MorphingParameter(
        fs=fs,
        frame_period=frame_period,
        base_f0=base_f0,
        base_aperiodicity=base_aperiodicity,
        base_spectrogram=base_spectrogram,
        target_spectrogram=target_spectrogram,
    )


def synthesis_morphing(
    morph_param: MorphingParameter,
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
