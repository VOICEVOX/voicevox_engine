from unittest import TestCase

from voicevox_engine.mora_list import openjtalk_mora2text


class TestOpenJTalkMoraList(TestCase):
    def test_mora2text(self):
        self.assertEqual("ッ", openjtalk_mora2text["cl"])
        self.assertEqual("ティ", openjtalk_mora2text["ti"])
        self.assertEqual("トゥ", openjtalk_mora2text["tu"])
        self.assertEqual("ディ", openjtalk_mora2text["di"])
        # GitHub issue #60
        self.assertEqual("ギェ", openjtalk_mora2text["gye"])
        self.assertEqual("イェ", openjtalk_mora2text["ye"])

    def test_mora2text_injective(self):
        """異なるモーラが同じ読みがなに対応しないか確認する"""
        values = list(openjtalk_mora2text.values())
        uniq_values = list(set(values))
        self.assertCountEqual(values, uniq_values)
