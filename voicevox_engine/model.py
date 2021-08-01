from typing import List, Optional

from pydantic import BaseModel


class Mora(BaseModel):
    text: str
    consonant: Optional[str]
    vowel: str
    pitch: float


class AccentPhrase(BaseModel):
    moras: List[Mora]
    accent: int
    pause_mora: Optional[Mora]


class AudioQuery(BaseModel):
    accent_phrases: List[AccentPhrase]
    speedScale: float
    pitchScale: float
    intonationScale: float
