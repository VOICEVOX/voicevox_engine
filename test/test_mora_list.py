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
        # GitHub issue #62
        self.assertEqual("shi", openjtalk_text2mora["シ"])
        self.assertEqual("si", openjtalk_text2mora["スィ"])
        self.assertEqual("zi", openjtalk_text2mora["ズィ"])
        self.assertEqual("ji", openjtalk_text2mora["ジ"])

    def test_bijection(self):
        # mora -> text -> mora
        for mora, text in openjtalk_mora2text.items():
            self.assertIn(text, openjtalk_text2mora)
            self.assertEqual(mora, openjtalk_text2mora[text])

        # text -> mora -> text
        for text, mora in openjtalk_text2mora.items():
            self.assertIn(mora, openjtalk_mora2text)
            self.assertEqual(text, openjtalk_mora2text[mora])
