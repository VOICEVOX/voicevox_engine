"""
ユーザー辞書機能に関して API と ENGINE 内部実装が共有するモデル（データ構造）

モデルの注意点は `voicevox_engine/model.py` の module docstring を確認すること。
"""

from enum import Enum
from re import fullmatch
from typing import Annotated, Self

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator
from pydantic.json_schema import SkipJsonSchema

from ..utility.text_utility import count_mora, replace_hankaku_alphabets_with_zenkaku


class WordTypes(str, Enum):
    """品詞"""

    PROPER_NOUN = "PROPER_NOUN"
    COMMON_NOUN = "COMMON_NOUN"
    VERB = "VERB"
    ADJECTIVE = "ADJECTIVE"
    SUFFIX = "SUFFIX"


USER_DICT_MIN_PRIORITY = 0
USER_DICT_MAX_PRIORITY = 10


def _check_newlines_and_null(text: str) -> str:
    if "\n" in text or "\r" in text:
        raise ValueError("ユーザー辞書データ内に改行が含まれています。")
    if "\x00" in text:
        raise ValueError("ユーザー辞書データ内にnull文字が含まれています。")
    return text


def _check_comma_and_double_quote(text: str) -> str:
    if "," in text:
        raise ValueError("ユーザー辞書データ内にカンマが含まれています。")
    if '"' in text:
        raise ValueError("ユーザー辞書データ内にダブルクォートが含まれています。")
    return text


def _check_is_katakana(pronunciation: str) -> str:
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


CsvSafeStr = Annotated[
    str,
    AfterValidator(_check_newlines_and_null),
    AfterValidator(_check_comma_and_double_quote),
]


class UserDictWord(BaseModel):
    """辞書のコンパイルに使われる情報。"""

    model_config = ConfigDict(validate_assignment=True)

    surface: Annotated[
        str,
        AfterValidator(replace_hankaku_alphabets_with_zenkaku),
        AfterValidator(_check_newlines_and_null),
    ] = Field(description="表層形")
    priority: int = Field(
        description="優先度", ge=USER_DICT_MIN_PRIORITY, le=USER_DICT_MAX_PRIORITY
    )
    context_id: int = Field(description="文脈ID", default=1348)
    part_of_speech: CsvSafeStr = Field(description="品詞")
    part_of_speech_detail_1: CsvSafeStr = Field(description="品詞細分類1")
    part_of_speech_detail_2: CsvSafeStr = Field(description="品詞細分類2")
    part_of_speech_detail_3: CsvSafeStr = Field(description="品詞細分類3")
    inflectional_type: CsvSafeStr = Field(description="活用型")
    inflectional_form: CsvSafeStr = Field(description="活用形")
    stem: CsvSafeStr = Field(description="原形")
    yomi: CsvSafeStr = Field(description="読み")
    pronunciation: Annotated[CsvSafeStr, AfterValidator(_check_is_katakana)] = Field(
        description="発音"
    )
    accent_type: int = Field(description="アクセント型")
    mora_count: int | SkipJsonSchema[None] = Field(default=None, description="モーラ数")
    accent_associative_rule: CsvSafeStr = Field(description="アクセント結合規則")

    @model_validator(mode="after")
    def check_mora_count_and_accent_type(self) -> Self:
        """モーラ数が None であれば計算し、アクセント型を検証する。"""
        # TODO: 2つの機能を２つの関数に分けるのが正しいか検討
        # モーラ数を計算し代入する
        if self.mora_count is None:
            self.mora_count = count_mora(self.pronunciation)
        # アクセント型を検証する
        if not 0 <= self.accent_type <= self.mora_count:
            msg = f"誤ったアクセント型です({self.accent_type})。 expect: 0 <= accent_type <= {self.mora_count}"
            raise ValueError(msg)
        return self
