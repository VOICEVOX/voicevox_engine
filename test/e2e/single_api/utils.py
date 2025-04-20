"""単独 API に対する E2E テスト共通のユーティリティ。"""

from typing import TypedDict


class _MoraForTest(TypedDict):
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
) -> _MoraForTest:
    """モーラを生成する。"""
    return {
        "text": text,
        "consonant": consonant,
        "consonant_length": consonant_length,
        "vowel": vowel,
        "vowel_length": vowel_length,
        "pitch": pitch,
    }
