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
    values = list(mora_phonemes_to_mora_kana.values())
    uniq_values = list(set(values))
    assert sorted(values) == sorted(uniq_values)
