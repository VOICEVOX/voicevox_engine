from voicevox_engine.tts_pipeline.mora_mapping import mora_phonemes_to_mora_kana


def test_mora2text() -> None:
    assert "ッ" == mora_phonemes_to_mora_kana["cl"]
    assert "ティ" == mora_phonemes_to_mora_kana["ti"]
    assert "トゥ" == mora_phonemes_to_mora_kana["tu"]
    assert "ディ" == mora_phonemes_to_mora_kana["di"]
    # GitHub issue #60
    assert "ギェ" == mora_phonemes_to_mora_kana["gye"]
    assert "イェ" == mora_phonemes_to_mora_kana["ye"]


def test_mora2text_injective() -> None:
    """異なるモーラが同じ読みがなに対応しないか確認する"""
    mora_kanas = list(mora_phonemes_to_mora_kana.values())
    # NOTE: 同じ読みがなが複数回登場すると set で非重複化して全長が短くなる
    assert len(mora_kanas) == len(set(mora_kanas))
