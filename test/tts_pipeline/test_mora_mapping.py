from unittest import TestCase

from voicevox_engine.tts_pipeline.mora_mapping import mora_phonemes_to_mora_kana


class TestOpenJTalkMoraList(TestCase):
    def test_mora2text(self):
        self.assertEqual("ッ", mora_phonemes_to_mora_kana["cl"])
        self.assertEqual("ティ", mora_phonemes_to_mora_kana["ti"])
        self.assertEqual("トゥ", mora_phonemes_to_mora_kana["tu"])
        self.assertEqual("ディ", mora_phonemes_to_mora_kana["di"])
        # GitHub issue #60
        self.assertEqual("ギェ", mora_phonemes_to_mora_kana["gye"])
        self.assertEqual("イェ", mora_phonemes_to_mora_kana["ye"])

    def test_mora2text_injective(self):
        """異なるモーラが同じ読みがなに対応しないか確認する"""
        values = list(mora_phonemes_to_mora_kana.values())
        uniq_values = list(set(values))
        self.assertCountEqual(values, uniq_values)
