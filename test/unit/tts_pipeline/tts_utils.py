"""合成系テスト向けの utility"""

from voicevox_engine.tts_pipeline.model import Mora


def sec(frame: int) -> float:
    """フレーム数に相当する秒数を返す。"""
    return 0.01067 * frame  # 1 フレームが約 10.67 ミリ秒


def gen_mora(
    text: str,
    consonant: str | None,
    consonant_length: float | None,
    vowel: str,
    vowel_length: float,
    pitch: float,
) -> Mora:
    """Generate Mora with positional arguments for test simplicity."""
    return Mora(
        text=text,
        consonant=consonant,
        consonant_length=consonant_length,
        vowel=vowel,
        vowel_length=vowel_length,
        pitch=pitch,
    )
