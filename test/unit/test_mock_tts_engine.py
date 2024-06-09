from voicevox_engine.dev.tts_engine.mock import MockTTSEngine
from voicevox_engine.metas.Metas import StyleId
from voicevox_engine.model import AudioQuery
from voicevox_engine.tts_pipeline.kana_converter import create_kana
from voicevox_engine.tts_pipeline.model import AccentPhrase, Mora


def _gen_mora(text: str, consonant: str | None, vowel: str) -> Mora:
    """モーラ (length=0, pitch=0) を生成する"""
    return Mora(
        text=text,
        consonant=consonant,
        consonant_length=0.0 if consonant else None,
        vowel=vowel,
        vowel_length=0.0,
        pitch=0.0,
    )


def _gen_accent_phrases() -> list[AccentPhrase]:
    return [
        AccentPhrase(
            moras=[
                _gen_mora("コ", "k", "o"),
                _gen_mora("ン", None, "N"),
                _gen_mora("ニ", "n", "i"),
                _gen_mora("チ", "ch", "i"),
                _gen_mora("ワ", "w", "a"),
            ],
            accent=5,
            pause_mora=_gen_mora("、", None, "pau"),
        ),
        AccentPhrase(
            moras=[
                _gen_mora("ヒ", "h", "i"),
                _gen_mora("ホ", "h", "o"),
                _gen_mora("デ", "d", "e"),
                _gen_mora("ス", "s", "U"),
            ],
            accent=1,
            pause_mora=None,
        ),
    ]


def test_update_length() -> None:
    """`.update_length()` がエラー無く生成をおこなう"""
    engine = MockTTSEngine()
    engine.update_length(_gen_accent_phrases(), StyleId(0))


def test_update_pitch() -> None:
    """`.update_pitch()` がエラー無く生成をおこなう"""
    engine = MockTTSEngine()
    engine.update_pitch(_gen_accent_phrases(), StyleId(0))


def test_synthesize_wave() -> None:
    """`.synthesize_wave()` がエラー無く生成をおこなう"""
    engine = MockTTSEngine()
    engine.synthesize_wave(
        AudioQuery(
            accent_phrases=_gen_accent_phrases(),
            speedScale=1,
            pitchScale=0,
            intonationScale=1,
            volumeScale=1,
            prePhonemeLength=0.1,
            postPhonemeLength=0.1,
            pauseLength=None,
            pauseLengthScale=1.0,
            outputSamplingRate=24000,
            outputStereo=False,
            kana=create_kana(_gen_accent_phrases()),
        ),
        StyleId(0),
    )
