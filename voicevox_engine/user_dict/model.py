"""
ユーザー辞書機能に関して API と ENGINE 内部実装が共有するモデル（データ構造）

モデルの注意点は `voicevox_engine/model.py` の module docstring を確認すること。
"""

from enum import Enum
from re import findall, fullmatch
from typing import Self

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator
from pydantic.json_schema import SkipJsonSchema
from typing_extensions import Annotated


class WordTypes(str, Enum):
    """品詞"""

    PROPER_NOUN = "PROPER_NOUN"
    COMMON_NOUN = "COMMON_NOUN"
    VERB = "VERB"
    ADJECTIVE = "ADJECTIVE"
    SUFFIX = "SUFFIX"


USER_DICT_MIN_PRIORITY = 0
USER_DICT_MAX_PRIORITY = 10


def remove_newlines_and_null(text: str) -> str:
    return text.replace("\n", "").replace("\r", "").replace("\x00", "")


def remove_comma_and_double_quote(text: str) -> str:
    return text.replace(",", "").replace('"', "")


def convert_to_zenkaku(surface: str) -> str:
    return surface.translate(
        str.maketrans(
            "".join(chr(0x21 + i) for i in range(94)),
            "".join(chr(0xFF01 + i) for i in range(94)),
        )
    )


def check_is_katakana(pronunciation: str) -> str:
    if not fullmatch(r"[ァ-ヴー]+", pronunciation):
        raise ValueError("発音は有効なカタカナでなくてはいけません。")
    sutegana = ["ァ", "ィ", "ゥ", "ェ", "ォ", "ャ", "ュ", "ョ", "ヮ", "ッ"]
    for i in range(len(pronunciation)):
        if pronunciation[i] in sutegana:
            # 「キャット」のように、捨て仮名が連続する可能性が考えられるので、
            # 「ッ」に関しては「ッ」そのものが連続している場合と、「ッ」の後にほかの捨て仮名が連続する場合のみ無効とする
            if i < len(pronunciation) - 1 and (
                pronunciation[i + 1] in sutegana[:-1]
                or (
                    pronunciation[i] == sutegana[-1]
                    and pronunciation[i + 1] == sutegana[-1]
                )
            ):
                raise ValueError("無効な発音です。(捨て仮名の連続)")
        if pronunciation[i] == "ヮ":
            if i != 0 and pronunciation[i - 1] not in ["ク", "グ"]:
                raise ValueError("無効な発音です。(「くゎ」「ぐゎ」以外の「ゎ」の使用)")
    return pronunciation


SanitizedStr = Annotated[
    str,
    AfterValidator(remove_newlines_and_null),
    AfterValidator(remove_comma_and_double_quote),
]


class UserDictWord(BaseModel):
    """
    辞書のコンパイルに使われる情報
    """

    model_config = ConfigDict(validate_assignment=True)

    surface: Annotated[
        str,
        AfterValidator(convert_to_zenkaku),
        AfterValidator(remove_newlines_and_null),
    ] = Field(description="表層形")
    priority: int = Field(
        description="優先度", ge=USER_DICT_MIN_PRIORITY, le=USER_DICT_MAX_PRIORITY
    )
    context_id: int = Field(description="文脈ID", default=1348)
    part_of_speech: SanitizedStr = Field(description="品詞")
    part_of_speech_detail_1: SanitizedStr = Field(description="品詞細分類1")
    part_of_speech_detail_2: SanitizedStr = Field(description="品詞細分類2")
    part_of_speech_detail_3: SanitizedStr = Field(description="品詞細分類3")
    inflectional_type: SanitizedStr = Field(description="活用型")
    inflectional_form: SanitizedStr = Field(description="活用形")
    stem: SanitizedStr = Field(description="原形")
    yomi: SanitizedStr = Field(description="読み")
    pronunciation: Annotated[SanitizedStr, AfterValidator(check_is_katakana)] = Field(
        description="発音"
    )
    accent_type: int = Field(description="アクセント型")
    mora_count: int | SkipJsonSchema[None] = Field(default=None, description="モーラ数")
    accent_associative_rule: SanitizedStr = Field(description="アクセント結合規則")

    @model_validator(mode="after")
    def check_mora_count_and_accent_type(self) -> Self:
        if self.mora_count is None:
            rule_others = (
                "[イ][ェ]|[ヴ][ャュョ]|[ウクグトド][ゥ]|[テデ][ィェャュョ]|[クグ][ヮ]"
            )
            rule_line_i = "[キシチニヒミリギジヂビピ][ェャュョ]|[キニヒミリギビピ][ィ]"
            rule_line_u = "[クツフヴグ][ァ]|[ウクスツフヴグズ][ィ]|[ウクツフヴグ][ェォ]"
            rule_one_mora = "[ァ-ヴー]"
            self.mora_count = len(
                findall(
                    f"(?:{rule_others}|{rule_line_i}|{rule_line_u}|{rule_one_mora})",
                    self.pronunciation,
                )
            )

        if not 0 <= self.accent_type <= self.mora_count:
            raise ValueError(
                "誤ったアクセント型です({})。 expect: 0 <= accent_type <= {}".format(
                    self.accent_type, self.mora_count
                )
            )
        return self
