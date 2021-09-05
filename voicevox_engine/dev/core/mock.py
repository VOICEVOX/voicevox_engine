from logging import getLogger
from typing import Any, Dict, List

import numpy as np


def initialize(*args: List[Any]) -> None:
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
    logger = getLogger("uvicorn")  # FastAPI / Uvicorn 内からの利用のため
    logger.info(
        "Sorry, decode_forward() is a mock. Return values are incorrect.",
    )
    return np.ones(length * 256)
