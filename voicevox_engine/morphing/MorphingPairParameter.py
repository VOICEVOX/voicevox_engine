from dataclasses import dataclass
import numpy as np

from .MorphingQuery import MorphingQuery

# TODO: use pydantic.BaseModel?
# FIXME: ndarray type hint, https://github.com/JeremyCCHsu/Python-Wrapper-for-World-Vocoder/blob/2b64f86197573497c685c785c6e0e743f407b63e/pyworld/pyworld.pyx#L398
@dataclass(frozen=True)
class MorphingPairParameter:
    # key
    query: MorphingQuery

    fs: float
    frame_period: float
    base_f0: np.ndarray
    base_aperiodicity: np.ndarray
    base_spectrogram: np.ndarray
    target_spectrogram: np.ndarray
