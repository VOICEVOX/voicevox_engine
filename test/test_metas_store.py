import uuid

from voicevox_engine.metas.Metas import Speaker, SpeakerStyle, StyleId, StyleType
from voicevox_engine.metas.MetasStore import filter_speakers_and_styles


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
    result = filter_speakers_and_styles(
        [
            speaker_talk_only,
            speaker_singing_teacher_only,
            speaker_frame_decode_only,
            speaker_sing_only,
            speaker_allstyle,
        ],
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
    result = filter_speakers_and_styles(
        [
            speaker_talk_only,
            speaker_singing_teacher_only,
            speaker_frame_decode_only,
            speaker_sing_only,
            speaker_allstyle,
        ],
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
