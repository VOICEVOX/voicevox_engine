from typing import List, Optional

from .model import AccentPhrase, Mora, ParseKanaError, ParseKanaErrorCode
from .mora_list import openjtalk_text2mora

_LOOP_LIMIT = 300
_UNVOICE_SYMBOL = "_"
_ACCENT_SYMBOL = "'"
_NOPAUSE_DELIMITER = "/"
_PAUSE_DELIMITER = "、"
_WIDE_INTERROGATION_MARK = "？"

_text2mora_with_unvoice = {}
for text, (consonant, vowel) in openjtalk_text2mora.items():
    _text2mora_with_unvoice[text] = Mora(
        text=text,
        consonant=consonant if len(consonant) > 0 else None,
        consonant_length=0 if len(consonant) > 0 else None,
        vowel=vowel,
        vowel_length=0,
        pitch=0,
        is_interrogative=False,
    )
    if vowel in ["a", "i", "u", "e", "o"]:
        _text2mora_with_unvoice[_UNVOICE_SYMBOL + text] = Mora(
            text=text,
            consonant=consonant if len(consonant) > 0 else None,
            consonant_length=0 if len(consonant) > 0 else None,
            vowel=vowel.upper(),
            vowel_length=0,
            pitch=0,
            is_interrogative=False,
        )


def _text_to_accent_phrase(phrase: str) -> AccentPhrase:
    """
    longest matchにより読み仮名からAccentPhraseを生成
    入力長Nに対し計算量O(N^2)
    """
    accent_index: Optional[int] = None
    moras: List[Mora] = []

    base_index = 0  # パース開始位置。ここから右の文字列をstackに詰めていく。
    stack = ""  # 保留中の文字列
    matched_text: Optional[str] = None  # 保留中の文字列内で最後にマッチした仮名

    outer_loop = 0
    while base_index < len(phrase):
        outer_loop += 1
        if phrase[base_index] == _ACCENT_SYMBOL:
            if len(moras) == 0:
                raise ParseKanaError(ParseKanaErrorCode.ACCENT_TOP, text=phrase)
            if accent_index is not None:
                raise ParseKanaError(ParseKanaErrorCode.ACCENT_TWICE, text=phrase)
            accent_index = len(moras)
            base_index += 1
            continue
        for watch_index in range(base_index, len(phrase)):
            if phrase[watch_index] == _ACCENT_SYMBOL:
                break
            # 普通の文字の場合
            stack += phrase[watch_index]
            if stack in _text2mora_with_unvoice:
                matched_text = stack
        # push mora
        if matched_text is None:
            raise ParseKanaError(ParseKanaErrorCode.UNKNOWN_TEXT, text=stack)
        else:
            moras.append(_text2mora_with_unvoice[matched_text].copy(deep=True))
            base_index += len(matched_text)
            stack = ""
            matched_text = None
        if outer_loop > _LOOP_LIMIT:
            raise ParseKanaError(ParseKanaErrorCode.INFINITE_LOOP)
    if accent_index is None:
        raise ParseKanaError(ParseKanaErrorCode.ACCENT_NOTFOUND, text=phrase)
    else:
        return AccentPhrase(moras=moras, accent=accent_index, pause_mora=None)


def parse_kana(text: str) -> List[AccentPhrase]:
    """
    AquesTalk風記法テキストをパースして音長・音高未指定のaccent phraseに変換
    """

    parsed_results: List[AccentPhrase] = []
    phrase_base = 0
    if len(text) == 0:
        raise ParseKanaError(ParseKanaErrorCode.EMPTY_PHRASE, position=1)

    for i in range(len(text) + 1):
        if i == len(text) or text[i] in [_PAUSE_DELIMITER, _NOPAUSE_DELIMITER]:
            phrase = text[phrase_base:i]
            if len(phrase) == 0:
                raise ParseKanaError(
                    ParseKanaErrorCode.EMPTY_PHRASE,
                    position=str(len(parsed_results) + 1),
                )
            phrase_base = i + 1

            is_interrogative = _WIDE_INTERROGATION_MARK in phrase
            if is_interrogative:
                if _WIDE_INTERROGATION_MARK in phrase[:-1]:
                    raise ParseKanaError(
                        ParseKanaErrorCode.INTERROGATION_MARK_NOT_AT_END, text=phrase
                    )
                phrase = phrase.replace(_WIDE_INTERROGATION_MARK, "")

            accent_phrase: AccentPhrase = _text_to_accent_phrase(phrase)
            if i < len(text) and text[i] == _PAUSE_DELIMITER:
                accent_phrase.pause_mora = Mora(
                    text="、",
                    consonant=None,
                    consonant_length=None,
                    vowel="pau",
                    vowel_length=0,
                    pitch=0,
                )
            accent_phrase.is_interrogative = is_interrogative

            parsed_results.append(accent_phrase)

    return parsed_results


def create_kana(accent_phrases: List[AccentPhrase]) -> str:
    text = ""
    for i, phrase in enumerate(accent_phrases):
        for j, mora in enumerate(phrase.moras):
            if mora.vowel in ["A", "I", "U", "E", "O"]:
                text += _UNVOICE_SYMBOL

            text += mora.text
            if j + 1 == phrase.accent:
                text += _ACCENT_SYMBOL

        if phrase.is_interrogative:
            text += _WIDE_INTERROGATION_MARK

        if i < len(accent_phrases) - 1:
            if phrase.pause_mora is None:
                text += _NOPAUSE_DELIMITER
            else:
                text += _PAUSE_DELIMITER
    return text
