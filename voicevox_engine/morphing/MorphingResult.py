from dataclasses import dataclass

from .MorphingQuery import MorphingQuery
import numpy as np

# TODO: use pydantic.BaseModel?
@dataclass(frozen=True)
class MorphingResult:
    query: MorphingQuery

    generated: np.ndarray
