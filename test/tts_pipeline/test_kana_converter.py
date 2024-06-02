from unittest import TestCase

from voicevox_engine.tts_pipeline import kana_converter
from voicevox_engine.tts_pipeline.kana_converter import ParseKanaError, create_kana
from voicevox_engine.tts_pipeline.model import AccentPhrase, Mora, ParseKanaErrorCode


def parse_kana(text: str) -> list[AccentPhrase]:
    accent_phrases = kana_converter.parse_kana(text)
    return accent_phrases


def test_phrase_length() -> None:
    assert len(parse_kana("ア'/ア'")) == 2
    assert len(parse_kana("ア'、ア'")) == 2
    assert len(parse_kana("ア'/ア'/ア'/ア'/ア'")) == 5
    assert len(parse_kana("ス'")) == 1
    assert len(parse_kana("_ス'")) == 1
    assert len(parse_kana("ギェ'")) == 1
    assert len(parse_kana("ギェ'、ギェ'/ギェ'")) == 3


def test_accent() -> None:
    assert parse_kana("シャ'シシュシェショ")[0].accent == 1
    assert parse_kana("シャ'_シシュシェショ")[0].accent == 1
    assert parse_kana("シャシ'シュシェショ")[0].accent == 2
    assert parse_kana("シャ_シ'シュシェショ")[0].accent == 2
    assert parse_kana("シャシシュ'シェショ")[0].accent == 3
    assert parse_kana("シャ_シシュ'シェショ")[0].accent == 3
    assert parse_kana("シャシシュシェショ'")[0].accent == 5
    assert parse_kana("シャ_シシュシェショ'")[0].accent == 5


def test_mora_length() -> None:
    assert len(parse_kana("シャ'シシュシェショ")[0].moras) == 5
    assert len(parse_kana("シャ'_シシュシェショ")[0].moras) == 5
    assert len(parse_kana("シャシ'シュシェショ")[0].moras) == 5
    assert len(parse_kana("シャ_シ'シュシェショ")[0].moras) == 5
    assert len(parse_kana("シャシシュシェショ'")[0].moras) == 5
    assert len(parse_kana("シャ_シシュシェショ'")[0].moras) == 5


def test_pause() -> None:
    assert parse_kana("ア'/ア'")[0].pause_mora is None
    assert parse_kana("ア'/ア'")[1].pause_mora is None
    assert parse_kana("ア'、ア'")[0].pause_mora is not None
    assert parse_kana("ア'、ア'")[1].pause_mora is None


def test_unvoice() -> None:
    assert parse_kana("ス'")[0].moras[0].vowel == "u"
    assert parse_kana("_ス'")[0].moras[0].vowel == "U"


def test_roundtrip() -> None:
    for text in [
        "コンニチワ'",
        "ワタシワ'/シャチョオデ'_ス",
        "トテモ'、エラ'インデス",
    ]:
        assert create_kana(parse_kana(text)) == text

    for text in ["ヲ'", "ェ'"]:
        assert create_kana(parse_kana(text)) == text


def _accent_phrase_marks_base(
    text: str, expected_accent_phrases: list[AccentPhrase]
) -> None:
    accent_phrases = kana_converter.parse_kana(text)
    assert expected_accent_phrases == accent_phrases


def test_accent_phrase_marks() -> None:
    def a_slash_a_accent_phrases() -> list[AccentPhrase]:
        return [
            AccentPhrase(
                moras=[
                    Mora(
                        text="ア",
                        consonant=None,
                        consonant_length=None,
                        vowel="a",
                        vowel_length=0.0,
                        pitch=0.0,
                    ),
                ],
                accent=1,
                pause_mora=None,
            ),
            AccentPhrase(
                moras=[
                    Mora(
                        text="ア",
                        consonant=None,
                        consonant_length=None,
                        vowel="a",
                        vowel_length=0.0,
                        pitch=0.0,
                    ),
                ],
                accent=1,
                pause_mora=None,
            ),
        ]

    expected_accent_phrases = a_slash_a_accent_phrases()
    _accent_phrase_marks_base(
        text="ア'/ア'",
        expected_accent_phrases=expected_accent_phrases,
    )

    def a_jp_comma_a_accent_phrases() -> list[AccentPhrase]:
        return [
            AccentPhrase(
                moras=[
                    Mora(
                        text="ア",
                        consonant=None,
                        consonant_length=None,
                        vowel="a",
                        vowel_length=0.0,
                        pitch=0.0,
                    ),
                ],
                accent=1,
                pause_mora=Mora(
                    text="、",
                    consonant=None,
                    consonant_length=None,
                    vowel="pau",
                    vowel_length=0.0,
                    pitch=0.0,
                ),
            ),
            AccentPhrase(
                moras=[
                    Mora(
                        text="ア",
                        consonant=None,
                        consonant_length=None,
                        vowel="a",
                        vowel_length=0.0,
                        pitch=0.0,
                    ),
                ],
                accent=1,
                pause_mora=None,
            ),
        ]

    expected_accent_phrases = a_jp_comma_a_accent_phrases()
    _accent_phrase_marks_base(
        text="ア'、ア'",
        expected_accent_phrases=expected_accent_phrases,
    )

    def a_slash_a_slash_a_slash_a_slash_a_accent_phrases() -> list[AccentPhrase]:
        return [
            AccentPhrase(
                moras=[
                    Mora(
                        text="ア",
                        consonant=None,
                        consonant_length=None,
                        vowel="a",
                        vowel_length=0.0,
                        pitch=0.0,
                    ),
                ],
                accent=1,
                pause_mora=None,
            ),
            AccentPhrase(
                moras=[
                    Mora(
                        text="ア",
                        consonant=None,
                        consonant_length=None,
                        vowel="a",
                        vowel_length=0.0,
                        pitch=0.0,
                    ),
                ],
                accent=1,
                pause_mora=None,
            ),
            AccentPhrase(
                moras=[
                    Mora(
                        text="ア",
                        consonant=None,
                        consonant_length=None,
                        vowel="a",
                        vowel_length=0.0,
                        pitch=0.0,
                    ),
                ],
                accent=1,
                pause_mora=None,
            ),
            AccentPhrase(
                moras=[
                    Mora(
                        text="ア",
                        consonant=None,
                        consonant_length=None,
                        vowel="a",
                        vowel_length=0.0,
                        pitch=0.0,
                    ),
                ],
                accent=1,
                pause_mora=None,
            ),
            AccentPhrase(
                moras=[
                    Mora(
                        text="ア",
                        consonant=None,
                        consonant_length=None,
                        vowel="a",
                        vowel_length=0.0,
                        pitch=0.0,
                    ),
                ],
                accent=1,
                pause_mora=None,
            ),
        ]

    expected_accent_phrases = a_slash_a_slash_a_slash_a_slash_a_accent_phrases()
    _accent_phrase_marks_base(
        text="ア'/ア'/ア'/ア'/ア'",
        expected_accent_phrases=expected_accent_phrases,
    )

    def su_accent_phrases() -> list[AccentPhrase]:
        return [
            AccentPhrase(
                moras=[
                    Mora(
                        text="ス",
                        consonant="s",
                        consonant_length=0.0,
                        vowel="u",
                        vowel_length=0.0,
                        pitch=0.0,
                    ),
                ],
                accent=1,
                pause_mora=None,
            ),
        ]

    expected_accent_phrases = su_accent_phrases()
    _accent_phrase_marks_base(
        text="ス'",
        expected_accent_phrases=expected_accent_phrases,
    )

    def under_score_su_accent_phrases() -> list[AccentPhrase]:
        return [
            AccentPhrase(
                moras=[
                    Mora(
                        text="ス",
                        consonant="s",
                        consonant_length=0.0,
                        vowel="U",
                        vowel_length=0.0,
                        pitch=0.0,
                    ),
                ],
                accent=1,
                pause_mora=None,
            ),
        ]

    expected_accent_phrases = under_score_su_accent_phrases()
    _accent_phrase_marks_base(
        text="_ス'",
        expected_accent_phrases=expected_accent_phrases,
    )

    def gye_accent_phrases() -> list[AccentPhrase]:
        return [
            AccentPhrase(
                moras=[
                    Mora(
                        text="ギェ",
                        consonant="gy",
                        consonant_length=0.0,
                        vowel="e",
                        vowel_length=0.0,
                        pitch=0.0,
                    ),
                ],
                accent=1,
                pause_mora=None,
            ),
        ]

    expected_accent_phrases = gye_accent_phrases()
    _accent_phrase_marks_base(
        text="ギェ'",
        expected_accent_phrases=expected_accent_phrases,
    )

    def gye_gye_gye_accent_phrases() -> list[AccentPhrase]:
        return [
            AccentPhrase(
                moras=[
                    Mora(
                        text="ギェ",
                        consonant="gy",
                        consonant_length=0.0,
                        vowel="e",
                        vowel_length=0.0,
                        pitch=0.0,
                    ),
                ],
                accent=1,
                pause_mora=Mora(
                    text="、",
                    consonant=None,
                    consonant_length=None,
                    vowel="pau",
                    vowel_length=0.0,
                    pitch=0.0,
                ),
            ),
            AccentPhrase(
                moras=[
                    Mora(
                        text="ギェ",
                        consonant="gy",
                        consonant_length=0.0,
                        vowel="e",
                        vowel_length=0.0,
                        pitch=0.0,
                    ),
                ],
                accent=1,
                pause_mora=None,
            ),
            AccentPhrase(
                moras=[
                    Mora(
                        text="ギェ",
                        consonant="gy",
                        consonant_length=0.0,
                        vowel="e",
                        vowel_length=0.0,
                        pitch=0.0,
                    ),
                ],
                accent=1,
                pause_mora=None,
            ),
        ]

    expected_accent_phrases = gye_gye_gye_accent_phrases()
    _accent_phrase_marks_base(
        text="ギェ'、ギェ'/ギェ'",
        expected_accent_phrases=expected_accent_phrases,
    )


def test_interrogative_accent_phrase_marks() -> None:
    def a_question_mark_accent_phrases() -> list[AccentPhrase]:
        return [
            AccentPhrase(
                moras=[
                    Mora(
                        text="ア",
                        consonant=None,
                        consonant_length=None,
                        vowel="a",
                        vowel_length=0.0,
                        pitch=0.0,
                    ),
                ],
                accent=1,
                pause_mora=None,
                is_interrogative=True,
            ),
        ]

    expected_accent_phrases = a_question_mark_accent_phrases()
    _accent_phrase_marks_base(
        text="ア'？",
        expected_accent_phrases=expected_accent_phrases,
    )

    def gye_gye_gye_question_mark_accent_phrases() -> list[AccentPhrase]:
        return [
            AccentPhrase(
                moras=[
                    Mora(
                        text="ギェ",
                        consonant="gy",
                        consonant_length=0.0,
                        vowel="e",
                        vowel_length=0.0,
                        pitch=0.0,
                    ),
                ],
                accent=1,
                pause_mora=Mora(
                    text="、",
                    consonant=None,
                    consonant_length=None,
                    vowel="pau",
                    vowel_length=0.0,
                    pitch=0.0,
                ),
            ),
            AccentPhrase(
                moras=[
                    Mora(
                        text="ギェ",
                        consonant="gy",
                        consonant_length=0.0,
                        vowel="e",
                        vowel_length=0.0,
                        pitch=0.0,
                    ),
                ],
                accent=1,
                pause_mora=None,
            ),
            AccentPhrase(
                moras=[
                    Mora(
                        text="ギェ",
                        consonant="gy",
                        consonant_length=0.0,
                        vowel="e",
                        vowel_length=0.0,
                        pitch=0.0,
                    ),
                ],
                accent=1,
                pause_mora=None,
                is_interrogative=True,
            ),
        ]

    expected_accent_phrases = gye_gye_gye_question_mark_accent_phrases()
    _accent_phrase_marks_base(
        text="ギェ'、ギェ'/ギェ'？",
        expected_accent_phrases=expected_accent_phrases,
    )

    def a_pause_a_question_pause_a_question_a_question_mark_accent_phrases() -> (
        list[AccentPhrase]
    ):
        return [
            AccentPhrase(
                moras=[
                    Mora(
                        text="ア",
                        consonant=None,
                        consonant_length=None,
                        vowel="a",
                        vowel_length=0.0,
                        pitch=0.0,
                    ),
                ],
                accent=1,
                pause_mora=Mora(
                    text="、",
                    consonant=None,
                    consonant_length=None,
                    vowel="pau",
                    vowel_length=0.0,
                    pitch=0.0,
                ),
            ),
            AccentPhrase(
                moras=[
                    Mora(
                        text="ア",
                        consonant=None,
                        consonant_length=None,
                        vowel="a",
                        vowel_length=0.0,
                        pitch=0.0,
                    ),
                ],
                accent=1,
                pause_mora=Mora(
                    text="、",
                    consonant=None,
                    consonant_length=None,
                    vowel="pau",
                    vowel_length=0.0,
                    pitch=0.0,
                ),
                is_interrogative=True,
            ),
            AccentPhrase(
                moras=[
                    Mora(
                        text="ア",
                        consonant=None,
                        consonant_length=None,
                        vowel="a",
                        vowel_length=0.0,
                        pitch=0.0,
                    ),
                ],
                accent=1,
                pause_mora=None,
                is_interrogative=True,
            ),
            AccentPhrase(
                moras=[
                    Mora(
                        text="ア",
                        consonant=None,
                        consonant_length=None,
                        vowel="a",
                        vowel_length=0.0,
                        pitch=0.0,
                    ),
                ],
                accent=1,
                pause_mora=None,
                is_interrogative=True,
            ),
        ]

    expected_accent_phrases = (
        a_pause_a_question_pause_a_question_a_question_mark_accent_phrases()
    )
    _accent_phrase_marks_base(
        text="ア'、ア'？、ア'？/ア'？",
        expected_accent_phrases=expected_accent_phrases,
    )


class TestParseKanaException(TestCase):
    def _assert_error_code(self, kana: str, code: ParseKanaErrorCode) -> None:
        with self.assertRaises(ParseKanaError) as err:
            parse_kana(kana)
        self.assertEqual(err.exception.errcode, code)

    def test_exceptions(self) -> None:
        self._assert_error_code("アクセント", ParseKanaErrorCode.ACCENT_NOTFOUND)
        self._assert_error_code("'アクセント", ParseKanaErrorCode.ACCENT_TOP)
        self._assert_error_code("ア'ク'セント", ParseKanaErrorCode.ACCENT_TWICE)
        self._assert_error_code("ひ'らがな", ParseKanaErrorCode.UNKNOWN_TEXT)
        self._assert_error_code("__ス'", ParseKanaErrorCode.UNKNOWN_TEXT)
        self._assert_error_code("ア'/", ParseKanaErrorCode.EMPTY_PHRASE)
        self._assert_error_code("/ア'", ParseKanaErrorCode.EMPTY_PHRASE)
        self._assert_error_code("", ParseKanaErrorCode.EMPTY_PHRASE)

        with self.assertRaises(ParseKanaError) as err:
            parse_kana("ヒト'ツメ/フタツメ")
        self.assertEqual(err.exception.errcode, ParseKanaErrorCode.ACCENT_NOTFOUND)
        self.assertEqual(err.exception.kwargs, {"text": "フタツメ"})

        with self.assertRaises(ParseKanaError) as err:
            parse_kana("ア'/")
        self.assertEqual(err.exception.errcode, ParseKanaErrorCode.EMPTY_PHRASE)
        self.assertEqual(err.exception.kwargs, {"position": "2"})

        with self.assertRaises(ParseKanaError) as err:
            kana_converter.parse_kana("ア？ア'")
        self.assertEqual(
            err.exception.errcode, ParseKanaErrorCode.INTERROGATION_MARK_NOT_AT_END
        )


def test_create_kana_interrogative() -> None:
    def koreha_arimasuka_accent_phrases() -> list[AccentPhrase]:
        return [
            AccentPhrase(
                moras=[
                    Mora(
                        text="コ",
                        consonant="k",
                        consonant_length=2.5,
                        vowel="o",
                        vowel_length=2.5,
                        pitch=2.5,
                    ),
                    Mora(
                        text="レ",
                        consonant="r",
                        consonant_length=2.5,
                        vowel="e",
                        vowel_length=2.5,
                        pitch=2.5,
                    ),
                    Mora(
                        text="ワ",
                        consonant="w",
                        consonant_length=2.5,
                        vowel="a",
                        vowel_length=2.5,
                        pitch=2.5,
                    ),
                ],
                accent=3,
                pause_mora=None,
                is_interrogative=False,
            ),
            AccentPhrase(
                moras=[
                    Mora(
                        text="ア",
                        consonant=None,
                        consonant_length=None,
                        vowel="a",
                        vowel_length=2.5,
                        pitch=2.5,
                    ),
                    Mora(
                        text="リ",
                        consonant="r",
                        consonant_length=2.5,
                        vowel="i",
                        vowel_length=2.5,
                        pitch=2.5,
                    ),
                    Mora(
                        text="マ",
                        consonant="m",
                        consonant_length=2.5,
                        vowel="a",
                        vowel_length=2.5,
                        pitch=2.5,
                    ),
                    Mora(
                        text="ス",
                        consonant="s",
                        consonant_length=2.5,
                        vowel="U",
                        vowel_length=2.5,
                        pitch=2.5,
                    ),
                    Mora(
                        text="カ",
                        consonant="k",
                        consonant_length=2.5,
                        vowel="a",
                        vowel_length=2.5,
                        pitch=2.5,
                    ),
                ],
                accent=3,
                pause_mora=None,
                is_interrogative=False,
            ),
        ]

    accent_phrases = koreha_arimasuka_accent_phrases()
    assert create_kana(accent_phrases) == "コレワ'/アリマ'_スカ"

    accent_phrases = koreha_arimasuka_accent_phrases()
    accent_phrases[-1].is_interrogative = True
    assert create_kana(accent_phrases) == "コレワ'/アリマ'_スカ？"

    def kya_accent_phrases() -> list[AccentPhrase]:
        return [
            AccentPhrase(
                moras=[
                    Mora(
                        text="キャ",
                        consonant="ky",
                        consonant_length=2.5,
                        vowel="a",
                        vowel_length=2.5,
                        pitch=2.5,
                    ),
                    Mora(
                        text="ッ",
                        consonant=None,
                        consonant_length=None,
                        vowel="cl",
                        vowel_length=0.1,
                        pitch=0,
                    ),
                ],
                accent=1,
                pause_mora=None,
                is_interrogative=False,
            ),
        ]

    accent_phrases = kya_accent_phrases()
    assert create_kana(accent_phrases) == "キャ'ッ"

    accent_phrases = kya_accent_phrases()
    accent_phrases[-1].is_interrogative = True
    assert create_kana(accent_phrases) == "キャ'ッ？"
