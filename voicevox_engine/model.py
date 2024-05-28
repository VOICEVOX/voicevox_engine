from enum import Enum
from re import findall, fullmatch
from typing import Any

from pydantic import BaseModel, Field, StrictStr, validator

from voicevox_engine.tts_pipeline.model import AccentPhrase

from .metas.Metas import Speaker, SpeakerInfo


class AudioQuery(BaseModel):
    """
    音声合成用のクエリ
    """

    accent_phrases: list[AccentPhrase] = Field(title="アクセント句のリスト")
    speedScale: float = Field(title="全体の話速")
    pitchScale: float = Field(title="全体の音高")
    intonationScale: float = Field(title="全体の抑揚")
    volumeScale: float = Field(title="全体の音量")
    prePhonemeLength: float = Field(title="音声の前の無音時間")
    postPhonemeLength: float = Field(title="音声の後の無音時間")
    outputSamplingRate: int = Field(title="音声データの出力サンプリングレート")
    outputStereo: bool = Field(title="音声データをステレオ出力するか否か")
    kana: str | None = Field(
        title="[読み取り専用]AquesTalk 風記法によるテキスト。音声合成用のクエリとしては無視される"
    )

    def __hash__(self) -> int:
        items = [
            (k, tuple(v)) if isinstance(v, list) else (k, v)
            for k, v in self.__dict__.items()
        ]
        return hash(tuple(sorted(items)))


class MorphableTargetInfo(BaseModel):
    is_morphable: bool = Field(title="指定した話者に対してモーフィングの可否")
    # FIXME: add reason property
    # reason: str | None = Field(title="is_morphableがfalseである場合、その理由")


class StyleIdNotFoundError(LookupError):
    def __init__(self, style_id: int, *args: object, **kywrds: object) -> None:
        self.style_id = style_id
        super().__init__(f"style_id {style_id} is not found.", *args, **kywrds)


class LibrarySpeaker(BaseModel):
    """
    音声ライブラリに含まれる話者の情報
    """

    speaker: Speaker = Field(title="話者情報")
    speaker_info: SpeakerInfo = Field(title="話者の追加情報")


class BaseLibraryInfo(BaseModel):
    """
    音声ライブラリの情報
    """

    name: str = Field(title="音声ライブラリの名前")
    uuid: str = Field(title="音声ライブラリのUUID")
    version: str = Field(title="音声ライブラリのバージョン")
    download_url: str = Field(title="音声ライブラリのダウンロードURL")
    bytes: int = Field(title="音声ライブラリのバイト数")
    speakers: list[LibrarySpeaker] = Field(title="音声ライブラリに含まれる話者のリスト")


# 今後InstalledLibraryInfo同様に拡張する可能性を考え、モデルを分けている
class DownloadableLibraryInfo(BaseLibraryInfo):
    """
    ダウンロード可能な音声ライブラリの情報
    """

    pass


class InstalledLibraryInfo(BaseLibraryInfo):
    """
    インストール済み音声ライブラリの情報
    """

    uninstallable: bool = Field(title="アンインストール可能かどうか")


USER_DICT_MIN_PRIORITY = 0
USER_DICT_MAX_PRIORITY = 10


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


class WordTypes(str, Enum):
    """
    fastapiでword_type引数を検証する時に使用するクラス
    """

    PROPER_NOUN = "PROPER_NOUN"
    COMMON_NOUN = "COMMON_NOUN"
    VERB = "VERB"
    ADJECTIVE = "ADJECTIVE"
    SUFFIX = "SUFFIX"


class SupportedFeaturesInfo(BaseModel):
    """
    エンジンの機能の情報
    """

    support_adjusting_mora: bool = Field(title="モーラが調整可能かどうか")
    support_adjusting_speed_scale: bool = Field(title="話速が調整可能かどうか")
    support_adjusting_pitch_scale: bool = Field(title="音高が調整可能かどうか")
    support_adjusting_intonation_scale: bool = Field(title="抑揚が調整可能かどうか")
    support_adjusting_volume_scale: bool = Field(title="音量が調整可能かどうか")
    support_adjusting_silence_scale: bool = Field(
        title="前後の無音時間が調節可能かどうか"
    )
    support_interrogative_upspeak: bool = Field(
        title="疑似疑問文に対応しているかどうか"
    )
    support_switching_device: bool = Field(title="CPU/GPUの切り替えが可能かどうか")


class VvlibManifest(BaseModel):
    """
    vvlib(VOICEVOX Library)に関する情報
    """

    manifest_version: StrictStr = Field(title="マニフェストバージョン")
    name: StrictStr = Field(title="音声ライブラリ名")
    version: StrictStr = Field(title="音声ライブラリバージョン")
    uuid: StrictStr = Field(title="音声ライブラリのUUID")
    brand_name: StrictStr = Field(title="エンジンのブランド名")
    engine_name: StrictStr = Field(title="エンジン名")
    engine_uuid: StrictStr = Field(title="エンジンのUUID")
