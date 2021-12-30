from typing import List
from unittest import TestCase

from voicevox_engine import model, preset
from voicevox_engine.webapi import fastapi_model, fastapi_model_converter


class TestFastAPIModelConverter(TestCase):
    def _assert_equal_types(self, expected, actual):
        for i, e in enumerate(expected):
            self.assertEqual(type(e), type(actual[i]))

    def _assert_not_equal_types(self, expected, actual):
        for i, e in enumerate(expected):
            self.assertNotEqual(type(e), type(actual[i]))

    def _asserts(self, expected, given, actual):
        self.assertEqual(expected, actual)
        self.assertEqual(type(expected), type(actual))
        self.assertEqual(given, actual)
        self.assertNotEqual(type(given), type(actual))

    def _asserts_list(self, expected, given, actual):
        self.assertEqual(expected, actual)
        self._assert_equal_types(expected, actual)
        self.assertEqual(given, actual)
        self._assert_not_equal_types(given, actual)

    def _mora(self):
        return model.Mora(
            text="ハ",
            consonant="h",
            consonant_length=0.6,
            vowel="a",
            vowel_length=0.5,
            pitch=3.5,
        )

    def _fastapi_mora(self):
        return fastapi_model.Mora(
            text="ハ",
            consonant="h",
            consonant_length=0.6,
            vowel="a",
            vowel_length=0.5,
            pitch=3.5,
        )

    def test_from_model_mora(self):
        actual: fastapi_model.Mora = fastapi_model_converter.from_model_mora(
            self._mora()
        )
        self._asserts(expected=self._fastapi_mora(), given=self._mora(), actual=actual)

    def test_to_model_mora(self):
        actual: model.Mora = fastapi_model_converter.to_model_mora(self._fastapi_mora())
        self._asserts(expected=self._mora(), given=self._fastapi_mora(), actual=actual)

    def _moras(self):
        return [self._mora(), self._mora()]

    def _fastapi_moras(self):
        return [self._fastapi_mora(), self._fastapi_mora()]

    def test_from_model_moras(self):
        actual: List[fastapi_model.Mora] = fastapi_model_converter.from_model_moras(
            self._moras()
        )
        self._asserts_list(
            expected=self._fastapi_moras(), given=self._moras(), actual=actual
        )

    def test_to_model_moras(self):
        actual: List[model.Mora] = fastapi_model_converter.to_model_moras(
            self._fastapi_moras()
        )
        self._asserts_list(
            expected=self._moras(), given=self._fastapi_moras(), actual=actual
        )

    def _accent_phrase(self):
        return model.AccentPhrase(
            moras=self._moras(),
            accent=3,
            pause_mora=None,
        )

    def _fastapi_accent_phrase(self):
        return fastapi_model.AccentPhrase(
            moras=self._fastapi_moras(),
            accent=3,
            pause_mora=None,
        )

    def _pause_mora(self):
        return model.Mora(
            text="、",
            consonant=None,
            consonant_length=None,
            vowel="pau",
            vowel_length=0,
            pitch=0,
        )

    def _fastapi_pause_mora(self):
        return fastapi_model.Mora(
            text="、",
            consonant=None,
            consonant_length=None,
            vowel="pau",
            vowel_length=0,
            pitch=0,
        )

    def test_from_model_accent_phrase(self):
        actual: fastapi_model.AccentPhrase = (
            fastapi_model_converter.from_model_accent_phrase(self._accent_phrase())
        )
        self._asserts(
            expected=self._fastapi_accent_phrase(),
            given=self._accent_phrase(),
            actual=actual,
        )

        given = self._accent_phrase()
        given.pause_mora = self._pause_mora()
        expected = self._fastapi_accent_phrase()
        expected.pause_mora = self._fastapi_pause_mora()
        actual: fastapi_model.AccentPhrase = (
            fastapi_model_converter.from_model_accent_phrase(given)
        )
        self._asserts(expected=expected, given=given, actual=actual)

    def test_to_model_accent_phrase(self):
        actual: model.AccentPhrase = fastapi_model_converter.to_model_accent_phrase(
            self._fastapi_accent_phrase()
        )
        self._asserts(
            expected=self._accent_phrase(),
            given=self._fastapi_accent_phrase(),
            actual=actual,
        )

        given = self._fastapi_accent_phrase()
        given.pause_mora = self._fastapi_pause_mora()
        expected = self._accent_phrase()
        expected.pause_mora = self._pause_mora()
        actual: model.AccentPhrase = fastapi_model_converter.to_model_accent_phrase(
            given
        )
        self._asserts(expected=expected, given=given, actual=actual)

    def _accent_phrases(self):
        return [
            self._accent_phrase(),
            self._accent_phrase(),
        ]

    def _fastapi_accent_phrases(self):
        return [
            self._fastapi_accent_phrase(),
            self._fastapi_accent_phrase(),
        ]

    def test_from_model_accent_phrases(self):
        actual: List[
            fastapi_model.AccentPhrase
        ] = fastapi_model_converter.from_model_accent_phrases(self._accent_phrases())
        self._asserts_list(
            expected=self._fastapi_accent_phrases(),
            given=self._accent_phrases(),
            actual=actual,
        )

    def test_to_model_accent_phrases(self):
        actual: List[
            model.AccentPhrase
        ] = fastapi_model_converter.to_model_accent_phrases(
            self._fastapi_accent_phrases()
        )
        self._asserts_list(
            expected=self._accent_phrases(),
            given=self._fastapi_accent_phrases(),
            actual=actual,
        )

    def _audio_query(self):
        return model.AudioQuery(
            accent_phrases=self._accent_phrases(),
            speedScale=3.2,
            pitchScale=4,
            intonationScale=2.3,
            volumeScale=4.3,
            prePhonemeLength=1.3,
            postPhonemeLength=5.3,
            outputSamplingRate=3,
            outputStereo=True,
            kana="ア",
        )

    def _fastapi_audio_query(self):
        return fastapi_model.AudioQuery(
            accent_phrases=self._fastapi_accent_phrases(),
            speedScale=3.2,
            pitchScale=4,
            intonationScale=2.3,
            volumeScale=4.3,
            prePhonemeLength=1.3,
            postPhonemeLength=5.3,
            outputSamplingRate=3,
            outputStereo=True,
            kana="ア",
        )

    def test_from_model_audio_query(self):
        actual: fastapi_model.AudioQuery = (
            fastapi_model_converter.from_model_audio_query(self._audio_query())
        )
        self._asserts(
            expected=self._fastapi_audio_query(),
            given=self._audio_query(),
            actual=actual,
        )

    def test_to_model_audio_query(self):
        actual: model.AudioQuery = fastapi_model_converter.to_model_audio_query(
            self._fastapi_audio_query()
        )
        self._asserts(
            expected=self._audio_query(),
            given=self._fastapi_audio_query(),
            actual=actual,
        )

    def _speaker_style(self):
        return model.SpeakerStyle(
            name="speaker_style_name",
            id=3,
        )

    def _fastapi_speaker_style(self):
        return fastapi_model.SpeakerStyle(
            name="speaker_style_name",
            id=3,
        )

    def test_from_model_speaker_style(self):
        actual: fastapi_model.SpeakerStyle = (
            fastapi_model_converter.from_model_speaker_style(self._speaker_style())
        )
        self._asserts(
            expected=self._fastapi_speaker_style(),
            given=self._speaker_style(),
            actual=actual,
        )

    def test_to_model_speaker_style(self):
        actual: model.SpeakerStyle = fastapi_model_converter.to_model_speaker_style(
            self._fastapi_speaker_style()
        )
        self._asserts(
            expected=self._speaker_style(),
            given=self._fastapi_speaker_style(),
            actual=actual,
        )

    def _speaker(self):
        return model.Speaker(
            name="speakername",
            speaker_uuid="speakeruuid",
            styles=[self._speaker_style(), self._speaker_style()],
            version="1.3",
        )

    def _fastapi_speaker(self):
        return fastapi_model.Speaker(
            name="speakername",
            speaker_uuid="speakeruuid",
            styles=[self._fastapi_speaker_style(), self._fastapi_speaker_style()],
            version="1.3",
        )

    def test_from_model_speaker(self):
        actual: fastapi_model.Speaker = fastapi_model_converter.from_model_speaker(
            self._speaker()
        )
        self._asserts(
            expected=self._fastapi_speaker(), given=self._speaker(), actual=actual
        )

    def test_to_model_speaker(self):
        actual: model.Speaker = fastapi_model_converter.to_model_speaker(
            self._fastapi_speaker()
        )
        self._asserts(
            expected=self._speaker(), given=self._fastapi_speaker(), actual=actual
        )

    def _style_info(self):
        return model.StyleInfo(
            id=3,
            icon="style_info_icon",
            voice_samples=["sample1", "sample2"],
        )

    def _fastapi_style_info(self):
        return fastapi_model.StyleInfo(
            id=3,
            icon="style_info_icon",
            voice_samples=["sample1", "sample2"],
        )

    def test_from_model_style_info(self):
        actual: fastapi_model.StyleInfo = fastapi_model_converter.from_model_style_info(
            self._style_info()
        )
        self._asserts(
            expected=self._fastapi_style_info(), given=self._style_info(), actual=actual
        )

    def test_to_model_style_info(self):
        actual: model.StyleInfo = fastapi_model_converter.to_model_style_info(
            self._fastapi_style_info()
        )
        self._asserts(
            expected=self._style_info(), given=self._fastapi_style_info(), actual=actual
        )

    def _speaker_info(self):
        return model.SpeakerInfo(
            policy="speaker_info_policy",
            portrait="speaker_info_portrait",
            style_infos=[self._style_info(), self._style_info()],
        )

    def _fastapi_speaker_info(self):
        return fastapi_model.SpeakerInfo(
            policy="speaker_info_policy",
            portrait="speaker_info_portrait",
            style_infos=[self._fastapi_style_info(), self._fastapi_style_info()],
        )

    def test_from_model_speaker_info(self):
        actual: fastapi_model.SpeakerInfo = (
            fastapi_model_converter.from_model_speaker_info(self._speaker_info())
        )
        self._asserts(
            expected=self._fastapi_speaker_info(),
            given=self._speaker_info(),
            actual=actual,
        )

    def test_to_model_speaker_info(self):
        actual: model.SpeakerInfo = fastapi_model_converter.to_model_speaker_info(
            self._fastapi_speaker_info()
        )
        self._asserts(
            expected=self._speaker_info(),
            given=self._fastapi_speaker_info(),
            actual=actual,
        )

    def _preset(self):
        return preset.Preset(
            id=3,
            name="preset_name",
            speaker_uuid="speaker_uuid",
            style_id=4,
            speedScale=3.2,
            pitchScale=2.3,
            intonationScale=4.2,
            volumeScale=2.2,
            prePhonemeLength=1.1,
            postPhonemeLength=1.2,
        )

    def _fastapi_preset(self):
        return fastapi_model.Preset(
            id=3,
            name="preset_name",
            speaker_uuid="speaker_uuid",
            style_id=4,
            speedScale=3.2,
            pitchScale=2.3,
            intonationScale=4.2,
            volumeScale=2.2,
            prePhonemeLength=1.1,
            postPhonemeLength=1.2,
        )

    def test_from_model_preset(self):
        actual: fastapi_model.Preset = fastapi_model_converter.from_model_preset(
            self._preset()
        )
        self._asserts(
            expected=self._fastapi_preset(), given=self._preset(), actual=actual
        )

    def test_to_model_preset(self):
        actual: preset.Preset = fastapi_model_converter.to_model_preset(
            self._fastapi_preset()
        )
        self._asserts(
            expected=self._preset(), given=self._fastapi_preset(), actual=actual
        )

    def _presets(self):
        return [self._preset(), self._preset()]

    def _fastapi_presets(self):
        return [self._fastapi_preset(), self._fastapi_preset()]

    def test_from_model_presets(self):
        actual: List[fastapi_model.Preset] = fastapi_model_converter.from_model_presets(
            self._presets()
        )
        self._asserts_list(
            expected=self._fastapi_presets(),
            given=self._presets(),
            actual=actual,
        )
