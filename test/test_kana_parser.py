from typing import List
from unittest import TestCase

from voicevox_engine.kana_parser import create_kana, parse_kana
from voicevox_engine.model import ParseKanaError, ParseKanaErrorCode


class TestParseKana(TestCase):
    def test_phrase_length(self):
        self.assertEqual(len(parse_kana("ア'/ア'", False)[0]), 2)
        self.assertEqual(len(parse_kana("ア'、ア'", False)[0]), 2)
        self.assertEqual(len(parse_kana("ア'/ア'/ア'/ア'/ア'", False)[0]), 5)
        self.assertEqual(len(parse_kana("ス'", False)[0]), 1)
        self.assertEqual(len(parse_kana("_ス'", False)[0]), 1)
        self.assertEqual(len(parse_kana("ギェ'", False)[0]), 1)
        self.assertEqual(len(parse_kana("ギェ'、ギェ'/ギェ'", False)[0]), 3)

    def test_accent(self):
        self.assertEqual(parse_kana("シャ'シシュシェショ", False)[0][0].accent, 1)
        self.assertEqual(parse_kana("シャ'_シシュシェショ", False)[0][0].accent, 1)
        self.assertEqual(parse_kana("シャシ'シュシェショ", False)[0][0].accent, 2)
        self.assertEqual(parse_kana("シャ_シ'シュシェショ", False)[0][0].accent, 2)
        self.assertEqual(parse_kana("シャシシュ'シェショ", False)[0][0].accent, 3)
        self.assertEqual(parse_kana("シャ_シシュ'シェショ", False)[0][0].accent, 3)
        self.assertEqual(parse_kana("シャシシュシェショ'", False)[0][0].accent, 5)
        self.assertEqual(parse_kana("シャ_シシュシェショ'", False)[0][0].accent, 5)

    def test_mora_length(self):
        self.assertEqual(len(parse_kana("シャ'シシュシェショ", False)[0][0].moras), 5)
        self.assertEqual(len(parse_kana("シャ'_シシュシェショ", False)[0][0].moras), 5)
        self.assertEqual(len(parse_kana("シャシ'シュシェショ", False)[0][0].moras), 5)
        self.assertEqual(len(parse_kana("シャ_シ'シュシェショ", False)[0][0].moras), 5)
        self.assertEqual(len(parse_kana("シャシシュシェショ'", False)[0][0].moras), 5)
        self.assertEqual(len(parse_kana("シャ_シシュシェショ'", False)[0][0].moras), 5)

    def test_pause(self):
        self.assertIsNone(parse_kana("ア'/ア'", False)[0][0].pause_mora)
        self.assertIsNone(parse_kana("ア'/ア'", False)[0][1].pause_mora)
        self.assertIsNotNone(parse_kana("ア'、ア'", False)[0][0].pause_mora)
        self.assertIsNone(parse_kana("ア'、ア'", False)[0][1].pause_mora)

    def test_unvoice(self):
        self.assertEqual(parse_kana("ス'", False)[0][0].moras[0].vowel, "u", False)
        self.assertEqual(parse_kana("_ス'", False)[0][0].moras[0].vowel, "U", False)

    def test_roundtrip(self):
        for text in ["コンニチワ'", "ワタシワ'/シャチョオデ'_ス", "トテモ'、エラ'インデス"]:
            self.assertEqual(create_kana(parse_kana(text, False)[0]), text)

        for text in ["ヲ'", "ェ'"]:
            self.assertEqual(create_kana(parse_kana(text, False)[0]), text)

    def _interrogative_accent_phrase_marks_base(
        self,
        text: str,
        enable_interrogative: bool,
        expected_interrogative_accent_phrase_marks: List[bool],
    ):
        accent_phrases, interrogative_accent_phrase_marks = parse_kana(
            text, enable_interrogative
        )
        self.assertEqual(len(accent_phrases), len(interrogative_accent_phrase_marks))
        self.assertEqual(
            interrogative_accent_phrase_marks,
            expected_interrogative_accent_phrase_marks,
        )

    def test_interrogative_accent_phrase_marks(self):
        self._interrogative_accent_phrase_marks_base(
            text="ア'/ア'",
            enable_interrogative=False,
            expected_interrogative_accent_phrase_marks=[False, False],
        )
        self._interrogative_accent_phrase_marks_base(
            text="ア'/ア'",
            enable_interrogative=True,
            expected_interrogative_accent_phrase_marks=[False, False],
        )

        self._interrogative_accent_phrase_marks_base(
            text="ア'、ア'",
            enable_interrogative=False,
            expected_interrogative_accent_phrase_marks=[False, False],
        )
        self._interrogative_accent_phrase_marks_base(
            text="ア'、ア'",
            enable_interrogative=True,
            expected_interrogative_accent_phrase_marks=[False, False],
        )

        self._interrogative_accent_phrase_marks_base(
            text="ア'/ア'/ア'/ア'/ア'",
            enable_interrogative=False,
            expected_interrogative_accent_phrase_marks=[
                False,
                False,
                False,
                False,
                False,
            ],
        )
        self._interrogative_accent_phrase_marks_base(
            text="ア'/ア'/ア'/ア'/ア'",
            enable_interrogative=True,
            expected_interrogative_accent_phrase_marks=[
                False,
                False,
                False,
                False,
                False,
            ],
        )

        self._interrogative_accent_phrase_marks_base(
            text="ス'",
            enable_interrogative=False,
            expected_interrogative_accent_phrase_marks=[False],
        )
        self._interrogative_accent_phrase_marks_base(
            text="ス'",
            enable_interrogative=True,
            expected_interrogative_accent_phrase_marks=[False],
        )

        self._interrogative_accent_phrase_marks_base(
            text="_ス'",
            enable_interrogative=False,
            expected_interrogative_accent_phrase_marks=[False],
        )
        self._interrogative_accent_phrase_marks_base(
            text="_ス'",
            enable_interrogative=True,
            expected_interrogative_accent_phrase_marks=[False],
        )

        self._interrogative_accent_phrase_marks_base(
            text="ギェ'",
            enable_interrogative=False,
            expected_interrogative_accent_phrase_marks=[False],
        )
        self._interrogative_accent_phrase_marks_base(
            text="ギェ'",
            enable_interrogative=True,
            expected_interrogative_accent_phrase_marks=[False],
        )

        self._interrogative_accent_phrase_marks_base(
            text="ギェ'、ギェ'/ギェ'",
            enable_interrogative=False,
            expected_interrogative_accent_phrase_marks=[False, False, False],
        )
        self._interrogative_accent_phrase_marks_base(
            text="ギェ'、ギェ'/ギェ'",
            enable_interrogative=True,
            expected_interrogative_accent_phrase_marks=[False, False, False],
        )

        self._interrogative_accent_phrase_marks_base(
            text="ア'？",
            enable_interrogative=False,
            expected_interrogative_accent_phrase_marks=[False],
        )

        self._interrogative_accent_phrase_marks_base(
            text="ア'？",
            enable_interrogative=True,
            expected_interrogative_accent_phrase_marks=[True],
        )

        self._interrogative_accent_phrase_marks_base(
            text="ギェ'、ギェ'/ギェ'？",
            enable_interrogative=False,
            expected_interrogative_accent_phrase_marks=[False, False, False],
        )

        self._interrogative_accent_phrase_marks_base(
            text="ギェ'、ギェ'/ギェ'？",
            enable_interrogative=True,
            expected_interrogative_accent_phrase_marks=[False, False, True],
        )


class TestParseKanaException(TestCase):
    def _assert_error_code(self, kana: str, code: ParseKanaErrorCode):
        with self.assertRaises(ParseKanaError) as err:
            parse_kana(kana, False)
        self.assertEqual(err.exception.errcode, code)

    def test_exceptions(self):
        self._assert_error_code("アクセント", ParseKanaErrorCode.ACCENT_NOTFOUND)
        self._assert_error_code("'アクセント", ParseKanaErrorCode.ACCENT_TOP)
        self._assert_error_code("ア'ク'セント", ParseKanaErrorCode.ACCENT_TWICE)
        self._assert_error_code("ひ'らがな", ParseKanaErrorCode.UNKNOWN_TEXT)
        self._assert_error_code("__ス'", ParseKanaErrorCode.UNKNOWN_TEXT)
        self._assert_error_code("ア'/", ParseKanaErrorCode.EMPTY_PHRASE)
        self._assert_error_code("/ア'", ParseKanaErrorCode.EMPTY_PHRASE)
        self._assert_error_code("ア？ア'", ParseKanaErrorCode.UNKNOWN_TEXT)

        with self.assertRaises(ParseKanaError) as err:
            parse_kana("ヒト'ツメ/フタツメ", False)
        self.assertEqual(err.exception.errcode, ParseKanaErrorCode.ACCENT_NOTFOUND)
        self.assertEqual(err.exception.kwargs, {"text": "フタツメ"})

        with self.assertRaises(ParseKanaError) as err:
            parse_kana("ア'/", False)
        self.assertEqual(err.exception.errcode, ParseKanaErrorCode.EMPTY_PHRASE)
        self.assertEqual(err.exception.kwargs, {"position": "2"})
