from typing import TypedDict


class MoraForTest(TypedDict):
    text: str
    consonant: str
    consonant_length: float
    vowel: str
    vowel_length: float
    pitch: float


def gen_mora(
    text: str,
    consonant: str,
    consonant_length: float,
    vowel: str,
    vowel_length: float,
    pitch: float,
) -> MoraForTest:
    return {
        "text": text,
        "consonant": consonant,
        "consonant_length": consonant_length,
        "vowel": vowel,
        "vowel_length": vowel_length,
        "pitch": pitch,
    }
