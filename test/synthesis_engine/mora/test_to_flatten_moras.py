from unittest import TestCase

from ...data_hello_hiho import accent_phrases_hello_hiho
from voicevox_engine.synthesis_engine.mora import to_flatten_moras

class TestToFlattenMoras(TestCase):
    def test_to_flatten_moras(self):
        flatten_moras = to_flatten_moras(accent_phrases_hello_hiho)
        self.assertEqual(
            flatten_moras,
            accent_phrases_hello_hiho[0].moras
            + [accent_phrases_hello_hiho[0].pause_mora]
            + accent_phrases_hello_hiho[1].moras,
        )
