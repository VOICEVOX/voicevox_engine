from unittest import TestCase

from voicevox_engine.tts_pipeline.mora_list import mora_alphabet_to_mora_katakana


class TestOpenJTalkMoraList(TestCase):
    def test_mora2text(self):
        self.assertEqual("ッ", mora_alphabet_to_mora_katakana["cl"])
        self.assertEqual("ティ", mora_alphabet_to_mora_katakana["ti"])
        self.assertEqual("トゥ", mora_alphabet_to_mora_katakana["tu"])
        self.assertEqual("ディ", mora_alphabet_to_mora_katakana["di"])
        # GitHub issue #60
        self.assertEqual("ギェ", mora_alphabet_to_mora_katakana["gye"])
        self.assertEqual("イェ", mora_alphabet_to_mora_katakana["ye"])

    def test_mora2text_injective(self):
        """異なるモーラが同じ読みがなに対応しないか確認する"""
        values = list(mora_alphabet_to_mora_katakana.values())
        uniq_values = list(set(values))
        self.assertCountEqual(values, uniq_values)
