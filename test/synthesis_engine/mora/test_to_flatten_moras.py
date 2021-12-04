from unittest import TestCase

from voicevox_engine.synthesis_engine.mora import to_flatten_moras

from ... import data_hello_hiho


class TestToFlattenMoras(TestCase):
    def test_to_flatten_moras(self):
        flatten_moras = to_flatten_moras(data_hello_hiho.accent_phrases)
        self.assertEqual(
            flatten_moras,
            data_hello_hiho.accent_phrases[0].moras
            + [data_hello_hiho.accent_phrases[0].pause_mora]
            + data_hello_hiho.accent_phrases[1].moras,
        )
