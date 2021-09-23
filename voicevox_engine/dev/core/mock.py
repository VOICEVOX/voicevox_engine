from logging import getLogger
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
from pyopenjtalk import tts
from resampy import resample

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
        本来はfloat64の入力でも問題ないのかと思われたが、実際には出力が音割れひどかった。
        対策として、あらかじめint16に型変換しておくと、期待通りの結果になった。
        非モックdecode_forwardと合わせるために、出力を24kHzに変換した。
    """
    logger = getLogger("uvicorn")  # FastAPI / Uvicorn 内からの利用のため
    logger.info(
        "Sorry, decode_forward() is a mock. Return values are incorrect.",
    )
    wave, sr = tts(DUMMY_TEXT)
    wave = resample(
        wave.astype("int16"),
        sr,
        24000,
        filter="kaiser_fast",
    )
    return wave


def metas() -> str:
    mock_dir = Path(__file__).parent
    version = (mock_dir / ".." / ".." / ".." / "VERSION.txt").read_text().strip()
    return str([
      {
        "name": "dummy1",
        "styles": [
          {
            "name": "dummy1",
            "id": 0
          }
        ],
        "speaker_uuid": "db447b10-0664-475e-95e6-785bca0a84eb",
        "version": version
      },
      {
        "name": "dummy2",
        "styles": [
          {
            "name": "dummy2",
            "id": 1
          }
        ],
        "speaker_uuid": "26067458-596a-482c-9a90-6c1d10d69c78",
        "version": version
      }
    ]).replace("'", '"')  # ちゃんとJSONとして認識してもらうためにシングルクォーテーションを置き換える
