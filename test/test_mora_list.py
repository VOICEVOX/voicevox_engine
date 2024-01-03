from unittest import TestCase

from voicevox_engine.tts_pipeline.mora_list import kana_mora2grapheme


class TestOpenJTalkMoraList(TestCase):
    def test_mora2text(self):
        self.assertEqual("ッ", kana_mora2grapheme["cl"])
        self.assertEqual("ティ", kana_mora2grapheme["ti"])
        self.assertEqual("トゥ", kana_mora2grapheme["tu"])
        self.assertEqual("ディ", kana_mora2grapheme["di"])
        # GitHub issue #60
        self.assertEqual("ギェ", kana_mora2grapheme["gye"])
        self.assertEqual("イェ", kana_mora2grapheme["ye"])

    def test_mora2text_injective(self):
        """異なるモーラが同じ読みがなに対応しないか確認する"""
        values = list(kana_mora2grapheme.values())
        uniq_values = list(set(values))
        self.assertCountEqual(values, uniq_values)
