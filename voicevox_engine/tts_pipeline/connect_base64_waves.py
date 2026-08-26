"""音声データの結合"""

import base64
import io

import numpy as np
import soundfile
from numpy.typing import NDArray
from soxr import resample

from ..utility.error_utility import UnreachableError


class ConnectBase64WavesException(Exception):
    """Base64 エンコードされた音声波形の結合に失敗した。"""

    def __init__(self, message: str):
        self.message = message


def decode_base64_waves(waves: list[str]) -> list[tuple[NDArray[np.float64], int]]:
    """
    base64エンコードされた複数のwavデータをデコードする

    Parameters
    ----------
    waves: list[str]
        base64エンコードされたwavデータのリスト

    Returns
    -------
    waves_nparray_sr: list[tuple[NDArray[np.float64], int]]
        (NumPy配列の音声波形データ, サンプリングレート) 形式のタプルのリスト
    """
    if len(waves) == 0:
        raise ConnectBase64WavesException("wavファイルが含まれていません")

    waves_nparray_sr = []
    for wave in waves:
        try:
            wav_bin = base64.standard_b64decode(wave)
        except ValueError as e:
            raise ConnectBase64WavesException("base64デコードに失敗しました") from e
        try:
            _data = soundfile.read(io.BytesIO(wav_bin))
        except Exception as e:
            raise ConnectBase64WavesException(
                "wavファイルを読み込めませんでした"
            ) from e
        waves_nparray_sr.append(_data)

    return waves_nparray_sr


def _get_channels(nparray: NDArray[np.float64]) -> int:
    if nparray.ndim == 1:
        return 1
    elif nparray.ndim == 2:
        return int(nparray.shape[1])
    else:
        msg = f"soundfileの読み込み結果のndimは1か2のはずですが、実際には{nparray.ndim}でした"
        raise UnreachableError(msg)


def connect_base64_waves(waves: list[str]) -> tuple[NDArray[np.float64], int]:
    """複数の base64 エンコードされた音声波形を1つに結合する。"""
    waves_nparray_sr = decode_base64_waves(waves)

    channels_list = [_get_channels(x) for x, _ in waves_nparray_sr]
    if not all(0 < channels <= 2 for channels in channels_list):
        msg = "1チャンネルまたは2チャンネル以外のwavファイルは非対応です"
        raise ConnectBase64WavesException(msg)
    max_channels = max(channels_list)

    max_sampling_rate = max([sr for _, sr in waves_nparray_sr])

    waves_nparray_list = []
    for (nparray, sr), channels in zip(waves_nparray_sr, channels_list, strict=True):
        if sr != max_sampling_rate:
            nparray = resample(nparray, sr, max_sampling_rate)
        if channels < max_channels:
            nparray = np.array([nparray, nparray]).T
        waves_nparray_list.append(nparray)

    return np.concatenate(waves_nparray_list), max_sampling_rate
