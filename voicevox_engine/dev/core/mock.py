import json
from logging import getLogger
from typing import Any, Dict, List

import numpy as np
from pyopenjtalk import tts
from soxr import resample

DUMMY_TEXT = "これはダミーのテキストです"


def initialize(path: str, use_gpu: bool, *args: List[Any]) -> None:
    pass


def yukarin_s_forward(length: int, **kwargs: Dict[str, Any]) -> np.ndarray:
    logger = getLogger("uvicorn")  # FastAPI / Uvicorn 内からの利用のため
    logger.info(
        "Sorry, yukarin_s_forward() is a mock. Return values are incorrect.",
    )
    return np.ones(length) / 5


def yukarin_sa_forward(length: int, **kwargs: Dict[str, Any]) -> np.ndarray:
    logger = getLogger("uvicorn")  # FastAPI / Uvicorn 内からの利用のため
    logger.info(
        "Sorry, yukarin_sa_forward() is a mock. Return values are incorrect.",
    )
    return np.ones((1, length)) * 5


def decode_forward(length: int, **kwargs: Dict[str, Any]) -> np.ndarray:
    """
    合成音声の波形データをNumPy配列で返します。ただし、常に固定の文言を読み上げます（DUMMY_TEXT）
    参照→SynthesisEngine のdocstring [Mock]

    Parameters
    ----------
    length : int
        フレームの長さ

    Returns
    -------
    wave : np.ndarray
        音声合成した波形データ

    Note
    -------
        ここで行う音声合成では、調声（ピッチ等）を反映しない
        また、入力内容によらず常に固定の文言を読み上げる

        # pyopenjtalk.tts()の出力仕様
        dtype=np.float64, 16 bit, mono 48000 Hz

        # resampleの説明
        非モックdecode_forwardと合わせるために、出力を24kHzに変換した。
    """
    logger = getLogger("uvicorn")  # FastAPI / Uvicorn 内からの利用のため
    logger.info(
        "Sorry, decode_forward() is a mock. Return values are incorrect.",
    )
    wave, sr = tts(DUMMY_TEXT)
    wave = resample(wave.astype("int16"), 48000, 24000)
    return wave


def metas() -> str:
    return json.dumps(
        [
            {
                "name": "dummy1",
                "styles": [
                    {"name": "style0", "id": 0},
                    {"name": "style1", "id": 2},
                    {"name": "style2", "id": 4},
                    {"name": "style3", "id": 6},
                ],
                "speaker_uuid": "7ffcb7ce-00ec-4bdc-82cd-45a8889e43ff",
                "version": "mock",
            },
            {
                "name": "dummy2",
                "styles": [
                    {"name": "style0", "id": 1},
                    {"name": "style1", "id": 3},
                    {"name": "style2", "id": 5},
                    {"name": "style3", "id": 7},
                ],
                "speaker_uuid": "388f246b-8c41-4ac1-8e2d-5d79f3ff56d9",
                "version": "mock",
            },
            {
                "name": "dummy3",
                "styles": [
                    {"name": "style0", "id": 8},
                ],
                "speaker_uuid": "35b2c544-660e-401e-b503-0e14c635303a",
                "version": "mock",
            },
            {
                "name": "dummy4",
                "styles": [
                    {"name": "style0", "id": 9},
                ],
                "speaker_uuid": "b1a81618-b27b-40d2-b0ea-27a9ad408c4b",
                "version": "mock",
            },
        ]
    )


def supported_devices() -> str:
    return json.dumps(
        {
            "cpu": True,
            "cuda": False,
        }
    )
