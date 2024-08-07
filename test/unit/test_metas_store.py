import uuid

from voicevox_engine.metas.Metas import (
    SpeakerStyle,
    SpeakerSupportedFeatures,
    StyleId,
    StyleType,
)
from voicevox_engine.metas.MetasStore import (
    _SING_STYLE_TYPES,
    _TALK_STYLE_TYPES,
    Character,
    filter_characters_and_styles,
)


def _gen_character(style_types: list[StyleType]) -> Character:
    talk_styles = list(filter(lambda s: s in _TALK_STYLE_TYPES, style_types))
    sing_styles = list(filter(lambda s: s in _SING_STYLE_TYPES, style_types))
    return Character(
        name="",
        uuid=str(uuid.uuid4()),
        talk_styles=[
            SpeakerStyle(name="", id=StyleId(0 + i), type=style_type)
            for i, style_type in enumerate(talk_styles)
        ],
        sing_styles=[
            SpeakerStyle(name="", id=StyleId(6000 + i), type=style_type)
            for i, style_type in enumerate(sing_styles)
        ],
        version="",
        supported_features=SpeakerSupportedFeatures(),
    )


def _equal_characters(a: list[Character], b: list[Character]) -> bool:
    if len(a) != len(b):
        return False
    for i in range(len(a)):
        if a[i].uuid != b[i].uuid:
            return False
    return True


def test_filter_characters_and_styles_with_talk() -> None:
    # Inputs
    talk_only = _gen_character(["talk"])
    singing_teacher_only = _gen_character(["singing_teacher"])
    frame_decode_only = _gen_character(["frame_decode"])
    sing_only = _gen_character(["sing"])
    allstyle = _gen_character(["talk", "singing_teacher", "frame_decode", "sing"])

    # Outputs
    result = filter_characters_and_styles(
        [talk_only, singing_teacher_only, frame_decode_only, sing_only, allstyle],
        "talk",
    )

    # Tests
    assert len(result) == 2

    # 喋れるキャラクターだけになっている
    assert _equal_characters(result, [talk_only, allstyle])

    # スタイルがフィルタリングされている
    for characters in result:
        for style in characters.talk_styles + characters.sing_styles:
            assert style.type == "talk"


def test_filter_characters_and_styles_with_sing() -> None:
    # Inputs
    talk_only = _gen_character(["talk"])
    singing_teacher_only = _gen_character(["singing_teacher"])
    frame_decode_only = _gen_character(["frame_decode"])
    sing_only = _gen_character(["sing"])
    allstyle = _gen_character(["talk", "singing_teacher", "frame_decode", "sing"])

    # Outputs
    result = filter_characters_and_styles(
        [talk_only, singing_teacher_only, frame_decode_only, sing_only, allstyle],
        "sing",
    )

    # Tests
    assert len(result) == 4

    # 歌えるキャラクターだけになっている
    assert _equal_characters(
        result, [singing_teacher_only, frame_decode_only, sing_only, allstyle]
    )

    # スタイルがフィルタリングされている
    for character in result:
        for style in character.talk_styles + character.sing_styles:
            assert style.type in ["singing_teacher", "frame_decode", "sing"]
