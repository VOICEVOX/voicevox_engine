import uuid
from unittest import TestCase

from voicevox_engine.metas.Metas import Speaker, SpeakerStyle, StyleType, StyleId
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


class TestMetasStore(TestCase):
    def test_filter_speakers_and_styles_with_speaker(self) -> None:
        # Inputs
        speaker_talk_only = _gen_speaker(["talk"])
        speaker_singing_teacher_only = _gen_speaker(["singing_teacher"])
        speaker_frame_decode_only = _gen_speaker(["frame_decode"])
        speaker_sing_only = _gen_speaker(["sing"])
        speaker_allstyle = _gen_speaker(
            ["talk", "singing_teacher", "frame_decode", "sing"]
        )

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
        self.assertEqual(len(result), 2)

        # 話者だけになっている
        self.assertTrue(_equal_speakers(result, [speaker_talk_only, speaker_allstyle]))

        # スタイルがフィルタリングされている
        for speaker in result:
            for style in speaker.styles:
                self.assertEqual(style.type, "talk")

    def test_filter_speakers_and_styles_with_singer(self) -> None:
        # Inputs
        speaker_talk_only = _gen_speaker(["talk"])
        speaker_singing_teacher_only = _gen_speaker(["singing_teacher"])
        speaker_frame_decode_only = _gen_speaker(["frame_decode"])
        speaker_sing_only = _gen_speaker(["sing"])
        speaker_allstyle = _gen_speaker(
            ["talk", "singing_teacher", "frame_decode", "sing"]
        )

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
        self.assertEqual(len(result), 4)

        # 歌手だけになっている
        self.assertTrue(
            _equal_speakers(
                result,
                [
                    speaker_singing_teacher_only,
                    speaker_frame_decode_only,
                    speaker_sing_only,
                    speaker_allstyle,
                ],
            )
        )

        # スタイルがフィルタリングされている
        for speaker in result:
            for style in speaker.styles:
                self.assertIn(style.type, ["singing_teacher", "frame_decode", "sing"])
