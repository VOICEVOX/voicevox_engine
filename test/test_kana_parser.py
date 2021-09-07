from unittest import TestCase

from pydantic import parse

from voicevox_engine.kana_parser import create_kana, parse_kana
from voicevox_engine.model import ParseKanaError, ParseKanaErrorCode


class TestParseKana(TestCase):
    def test_phrase_length(self):
        self.assertEqual(len(parse_kana("ア'/ア'")), 2)
        self.assertEqual(len(parse_kana("ア'、ア'")), 2)
        self.assertEqual(len(parse_kana("ア'/ア'/ア'/ア'/ア'")), 5)
        self.assertEqual(len(parse_kana("ス'")), 1)
        self.assertEqual(len(parse_kana("_ス'")), 1)
        self.assertEqual(len(parse_kana("ギェ'")), 1)
        self.assertEqual(len(parse_kana("ギェ'、ギェ'/ギェ'")), 3)

    def test_accent(self):
        self.assertEqual(parse_kana("シャ'シシュシェショ")[0].accent, 1)
        self.assertEqual(parse_kana("シャ'_シシュシェショ")[0].accent, 1)
        self.assertEqual(parse_kana("シャシ'シュシェショ")[0].accent, 2)
        self.assertEqual(parse_kana("シャ_シ'シュシェショ")[0].accent, 2)
        self.assertEqual(parse_kana("シャシシュ'シェショ")[0].accent, 3)
        self.assertEqual(parse_kana("シャ_シシュ'シェショ")[0].accent, 3)
        self.assertEqual(parse_kana("シャシシュシェショ'")[0].accent, 5)
        self.assertEqual(parse_kana("シャ_シシュシェショ'")[0].accent, 5)

    def test_mora_length(self):
        self.assertEqual(len(parse_kana("シャ'シシュシェショ")[0].moras), 5)
        self.assertEqual(len(parse_kana("シャ'_シシュシェショ")[0].moras), 5)
        self.assertEqual(len(parse_kana("シャシ'シュシェショ")[0].moras), 5)
        self.assertEqual(len(parse_kana("シャ_シ'シュシェショ")[0].moras), 5)
        self.assertEqual(len(parse_kana("シャシシュシェショ'")[0].moras), 5)
        self.assertEqual(len(parse_kana("シャ_シシュシェショ'")[0].moras), 5)

    def test_pause(self):
        self.assertIsNone(parse_kana("ア'/ア'")[0].pause_mora)
        self.assertIsNone(parse_kana("ア'/ア'")[1].pause_mora)
        self.assertIsNotNone(parse_kana("ア'、ア'")[0].pause_mora)
        self.assertIsNone(parse_kana("ア'、ア'")[1].pause_mora)

    def test_unvoice(self):
        self.assertEqual(parse_kana("ス'")[0].moras[0].vowel, "u")
        self.assertEqual(parse_kana("_ス'")[0].moras[0].vowel, "U")

    def test_roundtrip(self):
        for text in ["コンニチワ'", "ワタシワ'/シャチョオデ'_ス", "トテモ'、エラ'インデス"]:
            self.assertEqual(create_kana(parse_kana(text)), text)

        for text in ["ヲ'", "ェ'"]:
            self.assertEqual(create_kana(parse_kana(text)), text)


class TestParseKanaException(TestCase):
    def _assert_error_code(self, kana: str, code: ParseKanaErrorCode):
        with self.assertRaises(ParseKanaError) as err:
            parse_kana(kana)
        self.assertEqual(err.exception.errcode, code)

    def test_exceptions(self):
        self._assert_error_code("アクセント", ParseKanaErrorCode.ACCENT_NOTFOUND)
        self._assert_error_code("'アクセント", ParseKanaErrorCode.ACCENT_TOP)
        self._assert_error_code("ア'ク'セント", ParseKanaErrorCode.ACCENT_TWICE)
        self._assert_error_code("ひ'らがな", ParseKanaErrorCode.UNKNOWN_TEXT)
        self._assert_error_code("__ス'", ParseKanaErrorCode.UNKNOWN_TEXT)
        self._assert_error_code("ア'/", ParseKanaErrorCode.EMPTY_PHRASE)
        self._assert_error_code("/ア'", ParseKanaErrorCode.EMPTY_PHRASE)

        with self.assertRaises(ParseKanaError) as err:
            parse_kana("ヒト'ツメ/フタツメ")
        self.assertEqual(err.exception.errcode, ParseKanaErrorCode.ACCENT_NOTFOUND)
        self.assertEqual(err.exception.kwargs, {"text": "フタツメ"})

        with self.assertRaises(ParseKanaError) as err:
            parse_kana("ア'/")
        self.assertEqual(err.exception.errcode, ParseKanaErrorCode.EMPTY_PHRASE)
        self.assertEqual(err.exception.kwargs, {"position": "2"})
