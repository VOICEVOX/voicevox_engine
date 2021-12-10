from unittest import TestCase

# TODO: import from voicevox_engine.synthesis_engine.mora
from voicevox_engine.synthesis_engine.synthesis_engine_base import mora_to_text


class TestMoraToText(TestCase):
    def test_voice(self):
        self.assertEqual(mora_to_text("a"), "ア")
        self.assertEqual(mora_to_text("i"), "イ")
        self.assertEqual(mora_to_text("ka"), "カ")
        self.assertEqual(mora_to_text("N"), "ン")
        self.assertEqual(mora_to_text("cl"), "ッ")
        self.assertEqual(mora_to_text("gye"), "ギェ")
        self.assertEqual(mora_to_text("ye"), "イェ")
        self.assertEqual(mora_to_text("wo"), "ウォ")

    def test_unvoice(self):
        self.assertEqual(mora_to_text("A"), "ア")
        self.assertEqual(mora_to_text("I"), "イ")
        self.assertEqual(mora_to_text("kA"), "カ")
        self.assertEqual(mora_to_text("gyE"), "ギェ")
        self.assertEqual(mora_to_text("yE"), "イェ")
        self.assertEqual(mora_to_text("wO"), "ウォ")

    def test_invalid_mora(self):
        """変なモーラが来ても例外を投げない"""
        self.assertEqual(mora_to_text("x"), "x")
        self.assertEqual(mora_to_text(""), "")
