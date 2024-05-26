from enum import Enum
from re import findall, fullmatch
from typing import Any

from pydantic import BaseModel, Field, validator

USER_DICT_MIN_PRIORITY = 0
USER_DICT_MAX_PRIORITY = 10

MIN_PRIORITY = USER_DICT_MIN_PRIORITY
MAX_PRIORITY = USER_DICT_MAX_PRIORITY


class WordTypes(str, Enum):
    """
    fastapiでword_type引数を検証する時に使用するクラス
    """

    PROPER_NOUN = "PROPER_NOUN"
    COMMON_NOUN = "COMMON_NOUN"
    VERB = "VERB"
    ADJECTIVE = "ADJECTIVE"
    SUFFIX = "SUFFIX"


class PartOfSpeechDetail(BaseModel):
    """
    品詞ごとの情報
    """

    part_of_speech: str = Field(title="品詞")
    part_of_speech_detail_1: str = Field(title="品詞細分類1")
    part_of_speech_detail_2: str = Field(title="品詞細分類2")
    part_of_speech_detail_3: str = Field(title="品詞細分類3")
    # context_idは辞書の左・右文脈IDのこと
    # https://github.com/VOICEVOX/open_jtalk/blob/427cfd761b78efb6094bea3c5bb8c968f0d711ab/src/mecab-naist-jdic/_left-id.def # noqa
    context_id: int = Field(title="文脈ID")
    cost_candidates: list[int] = Field(title="コストのパーセンタイル")
    accent_associative_rules: list[str] = Field(title="アクセント結合規則の一覧")


part_of_speech_data: dict[WordTypes, PartOfSpeechDetail] = {
    WordTypes.PROPER_NOUN: PartOfSpeechDetail(
        part_of_speech="名詞",
        part_of_speech_detail_1="固有名詞",
        part_of_speech_detail_2="一般",
        part_of_speech_detail_3="*",
        context_id=1348,
        cost_candidates=[
            -988,
            3488,
            4768,
            6048,
            7328,
            8609,
            8734,
            8859,
            8984,
            9110,
            14176,
        ],
        accent_associative_rules=[
            "*",
            "C1",
            "C2",
            "C3",
            "C4",
            "C5",
        ],
    ),
    WordTypes.COMMON_NOUN: PartOfSpeechDetail(
        part_of_speech="名詞",
        part_of_speech_detail_1="一般",
        part_of_speech_detail_2="*",
        part_of_speech_detail_3="*",
        context_id=1345,
        cost_candidates=[
            -4445,
            49,
            1473,
            2897,
            4321,
            5746,
            6554,
            7362,
            8170,
            8979,
            15001,
        ],
        accent_associative_rules=[
            "*",
            "C1",
            "C2",
            "C3",
            "C4",
            "C5",
        ],
    ),
    WordTypes.VERB: PartOfSpeechDetail(
        part_of_speech="動詞",
        part_of_speech_detail_1="自立",
        part_of_speech_detail_2="*",
        part_of_speech_detail_3="*",
        context_id=642,
        cost_candidates=[
            3100,
            6160,
            6360,
            6561,
            6761,
            6962,
            7414,
            7866,
            8318,
            8771,
            13433,
        ],
        accent_associative_rules=[
            "*",
        ],
    ),
    WordTypes.ADJECTIVE: PartOfSpeechDetail(
        part_of_speech="形容詞",
        part_of_speech_detail_1="自立",
        part_of_speech_detail_2="*",
        part_of_speech_detail_3="*",
        context_id=20,
        cost_candidates=[
            1527,
            3266,
            3561,
            3857,
            4153,
            4449,
            5149,
            5849,
            6549,
            7250,
            10001,
        ],
        accent_associative_rules=[
            "*",
        ],
    ),
    WordTypes.SUFFIX: PartOfSpeechDetail(
        part_of_speech="名詞",
        part_of_speech_detail_1="接尾",
        part_of_speech_detail_2="一般",
        part_of_speech_detail_3="*",
        context_id=1358,
        cost_candidates=[
            4399,
            5373,
            6041,
            6710,
            7378,
            8047,
            9440,
            10834,
            12228,
            13622,
            15847,
        ],
        accent_associative_rules=[
            "*",
            "C1",
            "C2",
            "C3",
            "C4",
            "C5",
        ],
    ),
}


class UserDictWord(BaseModel):
    """
    辞書のコンパイルに使われる情報
    """

    surface: str = Field(title="表層形")
    priority: int = Field(
        title="優先度", ge=USER_DICT_MIN_PRIORITY, le=USER_DICT_MAX_PRIORITY
    )
    context_id: int = Field(title="文脈ID", default=1348)
    part_of_speech: str = Field(title="品詞")
    part_of_speech_detail_1: str = Field(title="品詞細分類1")
    part_of_speech_detail_2: str = Field(title="品詞細分類2")
    part_of_speech_detail_3: str = Field(title="品詞細分類3")
    inflectional_type: str = Field(title="活用型")
    inflectional_form: str = Field(title="活用形")
    stem: str = Field(title="原形")
    yomi: str = Field(title="読み")
    pronunciation: str = Field(title="発音")
    accent_type: int = Field(title="アクセント型")
    mora_count: int | None = Field(title="モーラ数")
    accent_associative_rule: str = Field(title="アクセント結合規則")

    class Config:
        validate_assignment = True

    @validator("surface")
    def convert_to_zenkaku(cls, surface: str) -> str:
        return surface.translate(
            str.maketrans(
                "".join(chr(0x21 + i) for i in range(94)),
                "".join(chr(0xFF01 + i) for i in range(94)),
            )
        )

    @validator("pronunciation", pre=True)
    def check_is_katakana(cls, pronunciation: str) -> str:
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
                    raise ValueError(
                        "無効な発音です。(「くゎ」「ぐゎ」以外の「ゎ」の使用)"
                    )
        return pronunciation

    @validator("mora_count", pre=True, always=True)
    def check_mora_count_and_accent_type(
        cls, mora_count: int | None, values: Any
    ) -> int | None:
        if "pronunciation" not in values or "accent_type" not in values:
            # 適切な場所でエラーを出すようにする
            return mora_count

        if mora_count is None:
            rule_others = (
                "[イ][ェ]|[ヴ][ャュョ]|[トド][ゥ]|[テデ][ィャュョ]|[デ][ェ]|[クグ][ヮ]"
            )
            rule_line_i = "[キシチニヒミリギジビピ][ェャュョ]"
            rule_line_u = "[ツフヴ][ァ]|[ウスツフヴズ][ィ]|[ウツフヴ][ェォ]"
            rule_one_mora = "[ァ-ヴー]"
            mora_count = len(
                findall(
                    f"(?:{rule_others}|{rule_line_i}|{rule_line_u}|{rule_one_mora})",
                    values["pronunciation"],
                )
            )

        if not 0 <= values["accent_type"] <= mora_count:
            raise ValueError(
                "誤ったアクセント型です({})。 expect: 0 <= accent_type <= {}".format(
                    values["accent_type"], mora_count
                )
            )
        return mora_count


class UserDictInputError(Exception):
    """受け入れ不可能な入力値に起因するエラー"""

    pass
