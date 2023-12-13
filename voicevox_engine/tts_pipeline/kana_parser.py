"""
「AquesTalk風記法」を実装した AquesTalk風記法テキスト <-> アクセント句系列 変換。
記法定義: `https://github.com/VOICEVOX/voicevox_engine/blob/master/README.md#読み方を-aquestalk風記法で取得修正するサンプルコード` # noqa
"""

from typing import List, Optional

from ..model import AccentPhrase, Mora, ParseKanaError, ParseKanaErrorCode
from .mora_list import openjtalk_text2mora

_LOOP_LIMIT = 300

# AquesTalk風記法特殊文字
_UNVOICE_SYMBOL = "_"  # 無声化
_ACCENT_SYMBOL = "'"  # アクセント位置
_NOPAUSE_DELIMITER = "/"  # ポーズ無しアクセント句境界
_PAUSE_DELIMITER = "、"  # ポーズ有りアクセント句境界
_WIDE_INTERROGATION_MARK = "？"  # 疑問形

# AquesTalk風記法とモーラの対応（音素長・音高 0 初期化、疑問形 off 初期化）
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
        # 手前に`_`を入れると無声化
        # 例: "_ホ" -> "hO"
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
    単一アクセント句に相当するAquesTalk風記法テキストからアクセント句オブジェクトを生成
    longest matchによりモーラ化。入力長Nに対し計算量O(N^2)。
    Parameters
    ----------
    phrase : str
        単一アクセント句に相当するAquesTalk風記法テキスト
    Returns
    -------
    accent_phrase : AccentPhrase
        アクセント句
    """
    # NOTE: ポーズと疑問形はこの関数内で処理しない

    accent_index: Optional[int] = None
    moras: List[Mora] = []

    base_index = 0  # パース開始位置。ここから右の文字列をstackに詰めていく。
    stack = ""  # 保留中の文字列
    matched_text: Optional[str] = None  # 保留中の文字列内で最後にマッチした仮名

    outer_loop = 0
    while base_index < len(phrase):
        outer_loop += 1

        # `'`の手前がアクセント位置
        if phrase[base_index] == _ACCENT_SYMBOL:
            if len(moras) == 0:
                raise ParseKanaError(ParseKanaErrorCode.ACCENT_TOP, text=phrase)
            # すでにアクセント位置がある場合はエラー
            if accent_index is not None:
                raise ParseKanaError(ParseKanaErrorCode.ACCENT_TWICE, text=phrase)
            accent_index = len(moras)
            base_index += 1
            continue

        # モーラ探索
        # より長い要素からなるモーラが見つかれば上書き（longest match）
        # 例: phrase "キャ" -> "キ" 検出 -> "キャ" 検出/上書き -> Mora("キャ")
        for watch_index in range(base_index, len(phrase)):
            # アクセント位置特殊文字が来たら探索打ち切り
            if phrase[watch_index] == _ACCENT_SYMBOL:
                break
            stack += phrase[watch_index]
            if stack in _text2mora_with_unvoice:
                # より長い要素からなるモーラが見つかれば上書き（longest match）
                # 例: phrase "キャ" -> "キ" 検出 -> "キャ" 検出/上書き -> Mora("キャ")
                matched_text = stack
        if matched_text is None:
            raise ParseKanaError(ParseKanaErrorCode.UNKNOWN_TEXT, text=stack)
        # push mora
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
    AquesTalk風記法テキストからアクセント句系列を生成
    Parameters
    ----------
    text : str
        AquesTalk風記法テキスト
    Returns
    -------
    parsed_results : List[AccentPhrase]
        アクセント句（音素・モーラ音高 0初期化）系列を生成
    """

    parsed_results: List[AccentPhrase] = []
    phrase_base = 0
    if len(text) == 0:
        raise ParseKanaError(ParseKanaErrorCode.EMPTY_PHRASE, position=1)

    for i in range(len(text) + 1):
        # アクセント句境界（`/`か`、`）の出現までインデックス進展
        if i == len(text) or text[i] in [_PAUSE_DELIMITER, _NOPAUSE_DELIMITER]:
            phrase = text[phrase_base:i]
            if len(phrase) == 0:
                raise ParseKanaError(
                    ParseKanaErrorCode.EMPTY_PHRASE,
                    position=str(len(parsed_results) + 1),
                )
            phrase_base = i + 1

            # アクセント句末に`？`で疑問文
            is_interrogative = _WIDE_INTERROGATION_MARK in phrase
            if is_interrogative:
                if _WIDE_INTERROGATION_MARK in phrase[:-1]:
                    raise ParseKanaError(
                        ParseKanaErrorCode.INTERROGATION_MARK_NOT_AT_END, text=phrase
                    )
                # 疑問形はモーラでなくアクセント句属性で表現
                phrase = phrase.replace(_WIDE_INTERROGATION_MARK, "")

            accent_phrase: AccentPhrase = _text_to_accent_phrase(phrase)

            # `、`で無音区間を挿入
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
    """
    アクセント句系列からAquesTalk風記法テキストを生成
    Parameters
    ----------
    accent_phrases : List[AccentPhrase]
        アクセント句系列
    Returns
    -------
    text : str
        AquesTalk風記法テキスト
    """
    text = ""
    # アクセント句を先頭から逐次パースし、`text`末尾にAquesTalk風記法の文字を都度追加（ループ）
    for i, phrase in enumerate(accent_phrases):
        for j, mora in enumerate(phrase.moras):
            # Rule3: "カナの手前に`_`を入れるとそのカナは無声化される"
            if mora.vowel in ["A", "I", "U", "E", "O"]:
                text += _UNVOICE_SYMBOL
            text += mora.text
            # `'`でアクセント位置
            if j + 1 == phrase.accent:
                text += _ACCENT_SYMBOL

        # Rule5: "アクセント句末に`？`(全角)を入れることにより疑問文の発音ができる"
        if phrase.is_interrogative:
            text += _WIDE_INTERROGATION_MARK

        if i < len(accent_phrases) - 1:
            if phrase.pause_mora is None:
                # アクセント句区切り
                text += _NOPAUSE_DELIMITER
            else:
                # 無音でアクセント句区切り
                text += _PAUSE_DELIMITER
    return text
