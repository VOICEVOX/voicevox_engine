from unittest import TestCase

from voicevox_engine.mora_list import (
    openjtalk_mora2text,
    openjtalk_text2mora
)

class TestOpenJTalkMoraList(TestCase):
    def test_mora2text(self):
        self.assertEqual("ッ", openjtalk_mora2text["cl"])
        self.assertEqual("ティ", openjtalk_mora2text["ti"])
        self.assertEqual("トゥ", openjtalk_mora2text["tu"])
        self.assertEqual("ディ", openjtalk_mora2text["di"])
        # GitHub issue #60
        self.assertEqual("ギェ", openjtalk_mora2text["gye"])
        self.assertEqual("イェ", openjtalk_mora2text["ye"])

    def test_text2mora(self):
        self.assertEqual("cl", openjtalk_text2mora["ッ"])
        self.assertEqual("ti", openjtalk_text2mora["ティ"])
        self.assertEqual("tu", openjtalk_text2mora["トゥ"])
        self.assertEqual("di", openjtalk_text2mora["ディ"])
        self.assertEqual("gye", openjtalk_text2mora["ギェ"])
        self.assertEqual("ye", openjtalk_text2mora["イェ"])

    def test_bijection(self):
        # mora -> text -> mora
        for mora, text in openjtalk_mora2text.items():
            self.assertIn(text, openjtalk_text2mora)
            self.assertEqual(mora, openjtalk_text2mora[text])

        # text -> mora -> text
        for text, mora in openjtalk_text2mora.items():
            self.assertIn(mora, openjtalk_mora2text)
            self.assertEqual(text, openjtalk_mora2text[mora])
