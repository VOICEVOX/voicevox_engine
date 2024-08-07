import hashlib
import io
from typing import Any

import numpy as np
import soundfile as sf
from fastapi.encoders import jsonable_encoder


def round_floats(value: Any, round_value: int) -> Any:
    """floatの小数点以下を再帰的に丸める"""
    if isinstance(value, float):
        return round(value, round_value)
    elif isinstance(value, np.ndarray) and np.issubdtype(value.dtype, np.floating):
        return np.round(value, round_value)
    elif isinstance(value, list):
        return [round_floats(v, round_value) for v in value]
    elif isinstance(value, dict):
        return {k: round_floats(v, round_value) for k, v in value.items()}
    else:
        return value


def pydantic_to_native_type(value: Any) -> Any:
    """pydanticの型をnativeな型に変換する"""
    return jsonable_encoder(value)


def hash_long_string(value: Any) -> Any:
    """文字数が1000文字を超えるものはハッシュ化する"""

    def to_hash(value: str) -> str:
        return "MD5:" + hashlib.md5(value.encode()).hexdigest()

    if isinstance(value, str):
        return value if len(value) <= 1000 else to_hash(value)
    elif isinstance(value, list):
        return [hash_long_string(v) for v in value]
    elif isinstance(value, dict):
        return {k: hash_long_string(v) for k, v in value.items()}
    else:
        return value


def summarize_big_ndarray(value: Any) -> Any:
    """要素数が100を超える NDArray を、ハッシュ値と shape からなる文字列へ要約する"""

    def to_hash(value: np.ndarray) -> str:
        return "MD5:" + hashlib.md5(value.tobytes()).hexdigest()

    if isinstance(value, np.ndarray):
        if value.size <= 100:
            return value
        else:
            return {"hash": to_hash(value), "shape": value.shape}
    elif isinstance(value, list):
        return [summarize_big_ndarray(v) for v in value]
    elif isinstance(value, dict):
        return {k: summarize_big_ndarray(v) for k, v in value.items()}
    else:
        return value


def hash_wave_floats_from_wav_bytes(wav_bytes: bytes) -> str:
    """.wavファイルバイト列から音声波形を抽出しハッシュ化する"""
    wave = sf.read(io.BytesIO(wav_bytes))[0].tolist()
    # NOTE: Linux-Windows 数値精度問題に対するワークアラウンド
    wave = round_floats(wave, 2)
    return "MD5:" + hashlib.md5(np.array(wave).tobytes()).hexdigest()
