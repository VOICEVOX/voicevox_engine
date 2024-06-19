import uuid

from voicevox_engine.metas.Metas import Speaker, SpeakerStyle, StyleId, StyleType
from voicevox_engine.metas.MetasStore import (
    SING_STYLE_TYPES,
    TALK_STYLE_TYPES,
    Character,
    filter_characters_and_styles,
)


def speakers_to_characters(speakers: list[Speaker]) -> list[Character]:
    """Speaker 配列をキャラクター配列へキャストする。"""
    characters: list[Character] = []
    for speaker in speakers:
        styles = speaker.styles
        talk_styles = filter(lambda style: style.type in TALK_STYLE_TYPES, styles)
        sing_styles = filter(lambda style: style.type in SING_STYLE_TYPES, styles)
        characters.append(
            Character(
                name=speaker.name,
                uuid=speaker.speaker_uuid,
                talk_styles=list(talk_styles),
                sing_styles=list(sing_styles),
                version=speaker.version,
                supported_features=speaker.supported_features,
            )
        )
    return characters


def _gen_speaker(style_types: list[StyleType]) -> Speaker:
    return Speaker(
        speaker_uuid=str(uuid.uuid4()),
        name="",
        styles=[
            SpeakerStyle(
                name="",
                id=StyleId(0),
                type=style_type,
            )
            for style_type in style_types
        ],
        version="",
    )


def _equal_speakers(a: list[Speaker], b: list[Speaker]) -> bool:
    if len(a) != len(b):
        return False
    for i in range(len(a)):
        if a[i].speaker_uuid != b[i].speaker_uuid:
            return False
    return True


def test_filter_speakers_and_styles_with_speaker() -> None:
    # Inputs
    speaker_talk_only = _gen_speaker(["talk"])
    speaker_singing_teacher_only = _gen_speaker(["singing_teacher"])
    speaker_frame_decode_only = _gen_speaker(["frame_decode"])
    speaker_sing_only = _gen_speaker(["sing"])
    speaker_allstyle = _gen_speaker(["talk", "singing_teacher", "frame_decode", "sing"])

    # Outputs
    result = filter_characters_and_styles(
        speakers_to_characters(
            [
                speaker_talk_only,
                speaker_singing_teacher_only,
                speaker_frame_decode_only,
                speaker_sing_only,
                speaker_allstyle,
            ]
        ),
        "speaker",
    )

    # Tests
    assert len(result) == 2

    # 話者だけになっている
    assert _equal_speakers(result, [speaker_talk_only, speaker_allstyle])

    # スタイルがフィルタリングされている
    for speaker in result:
        for style in speaker.styles:
            assert style.type == "talk"


def test_filter_speakers_and_styles_with_singer() -> None:
    # Inputs
    speaker_talk_only = _gen_speaker(["talk"])
    speaker_singing_teacher_only = _gen_speaker(["singing_teacher"])
    speaker_frame_decode_only = _gen_speaker(["frame_decode"])
    speaker_sing_only = _gen_speaker(["sing"])
    speaker_allstyle = _gen_speaker(["talk", "singing_teacher", "frame_decode", "sing"])

    # Outputs
    result = filter_characters_and_styles(
        speakers_to_characters(
            [
                speaker_talk_only,
                speaker_singing_teacher_only,
                speaker_frame_decode_only,
                speaker_sing_only,
                speaker_allstyle,
            ]
        ),
        "singer",
    )

    # Tests
    assert len(result) == 4

    # 歌手だけになっている
    assert _equal_speakers(
        result,
        [
            speaker_singing_teacher_only,
            speaker_frame_decode_only,
            speaker_sing_only,
            speaker_allstyle,
        ],
    )

    # スタイルがフィルタリングされている
    for speaker in result:
        for style in speaker.styles:
            assert style.type in ["singing_teacher", "frame_decode", "sing"]
