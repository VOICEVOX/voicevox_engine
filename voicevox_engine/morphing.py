from copy import deepcopy
from dataclasses import dataclass
from itertools import chain

import numpy as np
import pyworld as pw
from numpy.typing import NDArray
from soxr import resample

from .core_adapter import CoreAdapter
from .metas.Metas import (
    Speaker,
    SpeakerStyle,
    SpeakerSupportPermittedSynthesisMorphing,
    StyleId,
)
from .metas.MetasStore import construct_lookup
from .model import AudioQuery, MorphableTargetInfo, StyleIdNotFoundError
from .tts_pipeline import TTSEngine


@dataclass(frozen=True)
class MorphingParameter:
    fs: int
    frame_period: float
    base_f0: NDArray[np.double]
    base_aperiodicity: NDArray[np.double]
    base_spectrogram: NDArray[np.double]
    target_spectrogram: NDArray[np.double]


def create_morphing_parameter(
    base_wave: NDArray[np.double],
    target_wave: NDArray[np.double],
    fs: int,
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


def get_morphable_targets(
    speakers: list[Speaker],
    base_style_ids: list[StyleId],
) -> list[dict[StyleId, MorphableTargetInfo]]:
    """
    speakers: 全話者の情報
    base_speakers: モーフィング可能か判定したいベースのスタイルIDリスト
    """
    speaker_lookup = construct_lookup(speakers)

    morphable_targets_arr = []
    for base_style_id in base_style_ids:
        morphable_targets = dict()
        for style in chain.from_iterable(speaker.styles for speaker in speakers):
            morphable_targets[style.id] = MorphableTargetInfo(
                is_morphable=is_synthesis_morphing_permitted(
                    speaker_lookup=speaker_lookup,
                    base_style_id=base_style_id,
                    target_style_id=style.id,
                )
            )
        morphable_targets_arr.append(morphable_targets)

    return morphable_targets_arr


def is_synthesis_morphing_permitted(
    speaker_lookup: dict[StyleId, tuple[Speaker, SpeakerStyle]],
    base_style_id: StyleId,
    target_style_id: StyleId,
) -> bool:
    """
    指定されたstyle_idがモーフィング可能かどうか返す
    style_idが見つからない場合はStyleIdNotFoundErrorを送出する
    """

    base_speaker_data = speaker_lookup[base_style_id]
    target_speaker_data = speaker_lookup[target_style_id]

    if base_speaker_data is None or target_speaker_data is None:
        raise StyleIdNotFoundError(
            base_style_id if base_speaker_data is None else target_style_id
        )

    base_speaker_info, _ = base_speaker_data
    target_speaker_info, _ = target_speaker_data

    base_speaker_uuid = base_speaker_info.speaker_uuid
    target_speaker_uuid = target_speaker_info.speaker_uuid

    base_speaker_morphing_info: SpeakerSupportPermittedSynthesisMorphing = (
        base_speaker_info.supported_features.permitted_synthesis_morphing
    )

    target_speaker_morphing_info: SpeakerSupportPermittedSynthesisMorphing = (
        target_speaker_info.supported_features.permitted_synthesis_morphing
    )

    # 禁止されている場合はFalse
    if (
        base_speaker_morphing_info == SpeakerSupportPermittedSynthesisMorphing.NOTHING
        or target_speaker_morphing_info
        == SpeakerSupportPermittedSynthesisMorphing.NOTHING
    ):
        return False
    # 同一話者のみの場合は同一話者判定
    if (
        base_speaker_morphing_info == SpeakerSupportPermittedSynthesisMorphing.SELF_ONLY
        or target_speaker_morphing_info
        == SpeakerSupportPermittedSynthesisMorphing.SELF_ONLY
    ):
        return base_speaker_uuid == target_speaker_uuid
    # 念のため許可されているかチェック
    return (
        base_speaker_morphing_info == SpeakerSupportPermittedSynthesisMorphing.ALL
        and target_speaker_morphing_info == SpeakerSupportPermittedSynthesisMorphing.ALL
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

    base_wave = engine.synthesize_wave(query, base_style_id).astype("float")
    target_wave = engine.synthesize_wave(query, target_style_id).astype("float")

    return create_morphing_parameter(
        base_wave=base_wave,
        target_wave=target_wave,
        fs=query.outputSamplingRate,
    )


def synthesis_morphing(
    morph_param: MorphingParameter,
    morph_rate: float,
    output_fs: int,
    output_stereo: bool = False,
) -> NDArray[np.float64]:
    """
    指定した割合で、パラメータをもとにモーフィングした音声を生成します。

    Parameters
    ----------
    morph_param : MorphingParameter
        `synthesis_morphing_parameter`または`create_morphing_parameter`で作成したパラメータ

    morph_rate : float
        モーフィングの割合
        0.0でベースの音声、1.0でターゲットの音声に近づきます。

    Returns
    -------
    generated : NDArray[np.float64]
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

    # TODO: tts_engine.py でのリサンプル処理と共通化する
    if output_fs != morph_param.fs:
        y_h = resample(y_h, morph_param.fs, output_fs)

    if output_stereo:
        y_h = np.array([y_h, y_h]).T

    return y_h
