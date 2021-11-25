import base64
import io
from typing import List, Tuple

import numpy as np
import soundfile


class ConnectBase64WavesException(Exception):
    def __init__(self, message: str):
        self.message = message


def decode_base64_waves(waves: List[str]) -> Tuple[List[np.ndarray], float]:
    if len(waves) == 0:
        raise ConnectBase64WavesException("wavファイルが含まれていません")

    waves_nparray = []
    for i in range(len(waves)):
        try:
            wav_bin = base64.standard_b64decode(waves[i])
        except ValueError:
            raise ConnectBase64WavesException("base64デコードに失敗しました")
        try:
            _data, _sampling_rate = soundfile.read(io.BytesIO(wav_bin))
        except Exception:
            raise ConnectBase64WavesException("wavファイルを読み込めませんでした")
        if i == 0:
            sampling_rate = _sampling_rate
            channels = _data.ndim
        else:
            if sampling_rate != _sampling_rate:
                raise ConnectBase64WavesException("ファイル間でサンプリングレートが異なります")
            if channels != _data.ndim:
                if channels == 1:
                    _data = _data.T[0]
                else:
                    _data = np.array([_data, _data]).T
        waves_nparray.append(_data)

    return waves_nparray, sampling_rate


def connect_base64_waves(waves: List[str]) -> Tuple[np.ndarray, float]:
    waves_nparray_list, sampling_rate = decode_base64_waves(waves)
    return np.concatenate(waves_nparray_list), sampling_rate
