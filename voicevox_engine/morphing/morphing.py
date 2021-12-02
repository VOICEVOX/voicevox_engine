import numpy as np
import pyworld as pw

from .MorphingQuery import MorphingQuery
from .MorphingResult import MorphingResult

from .MorphingException import MorphingException
from .create_morphing_pair_parameter import create_morphing_pair_parameter


def morphing(query: MorphingQuery) -> MorphingResult:
    """
    指定された2人の話者で音声を合成、指定した割合でモーフィングした音声を得ます。
    モーフィングの割合は`morph_rate`で指定でき、0.0でベースの話者、1.0でターゲットの話者に近づきます。
    """

    if query.morph_rate < 0.0 or query.morph_rate > 1.0:
        raise MorphingException('morph_rateは0.0から1.0の範囲で指定してください')

    # WORLDに掛けるため合成はモノラルで行う
    output_stereo = query.outputStereo
    query.outputStereo = False

    morph_param = create_morphing_pair_parameter(query.audio_query, query.base_speaker, query.target_speaker)

    # スペクトルの重み付き結合
    morph_spectrogram = (
        morph_param.base_spectrogram * (1.0 - query.morph_rate) + morph_param.target_spectrogram * query.morph_rate
    )

    y_h = pw.synthesize(
        morph_param.base_f0, morph_spectrogram, morph_param.base_aperiodicity, morph_param.fs, morph_param.frame_period
    )

    if output_stereo:
        y_h = np.array([y_h, y_h]).T

    return MorphingResult(
        query=query,
        generated=y_h,
    )
