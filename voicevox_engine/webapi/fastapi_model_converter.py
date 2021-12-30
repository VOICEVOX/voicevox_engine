from typing import List

from voicevox_engine import model, preset
from voicevox_engine.webapi import fastapi_model


def from_model_mora(mora: model.Mora) -> fastapi_model.Mora:
    return fastapi_model.Mora(
        text=mora.text,
        consonant=mora.consonant,
        consonant_length=mora.consonant_length,
        vowel=mora.vowel,
        vowel_length=mora.vowel_length,
        pitch=mora.pitch,
    )


def from_model_moras(moras: List[model.Mora]) -> List[fastapi_model.Mora]:
    return [from_model_mora(mora) for mora in moras]


def to_model_mora(fastapi_mora: fastapi_model.Mora) -> model.Mora:
    return model.Mora(
        text=fastapi_mora.text,
        consonant=fastapi_mora.consonant,
        consonant_length=fastapi_mora.consonant_length,
        vowel=fastapi_mora.vowel,
        vowel_length=fastapi_mora.vowel_length,
        pitch=fastapi_mora.pitch,
    )


def to_model_moras(fastapi_moras: List[fastapi_model.Mora]) -> List[model.Mora]:
    return [to_model_mora(mora) for mora in fastapi_moras]


def from_model_accent_phrase(
    accent_phrase: model.AccentPhrase,
) -> fastapi_model.AccentPhrase:
    return fastapi_model.AccentPhrase(
        moras=from_model_moras(accent_phrase.moras),
        accent=accent_phrase.accent,
        pause_mora=from_model_mora(accent_phrase.pause_mora)
        if accent_phrase.pause_mora is not None
        else None,
    )


def from_model_accent_phrases(
    accent_phrases: List[model.AccentPhrase],
) -> List[fastapi_model.AccentPhrase]:
    return [from_model_accent_phrase(accent_phrase) for accent_phrase in accent_phrases]


def to_model_accent_phrase(
    fastapi_accent_phrase: fastapi_model.AccentPhrase,
) -> model.AccentPhrase:
    return model.AccentPhrase(
        moras=to_model_moras(fastapi_accent_phrase.moras),
        accent=fastapi_accent_phrase.accent,
        pause_mora=to_model_mora(fastapi_accent_phrase.pause_mora)
        if fastapi_accent_phrase.pause_mora is not None
        else None,
    )


def to_model_accent_phrases(
    fastapi_accent_phrases: List[fastapi_model.AccentPhrase],
) -> List[model.AccentPhrase]:
    return [
        to_model_accent_phrase(fastapi_accent_phrase)
        for fastapi_accent_phrase in fastapi_accent_phrases
    ]


def from_model_audio_query(audio_query: model.AudioQuery) -> fastapi_model.AudioQuery:
    return fastapi_model.AudioQuery(
        accent_phrases=from_model_accent_phrases(audio_query.accent_phrases),
        speedScale=audio_query.speedScale,
        pitchScale=audio_query.pitchScale,
        intonationScale=audio_query.intonationScale,
        volumeScale=audio_query.volumeScale,
        prePhonemeLength=audio_query.prePhonemeLength,
        postPhonemeLength=audio_query.postPhonemeLength,
        outputSamplingRate=audio_query.outputSamplingRate,
        outputStereo=audio_query.outputStereo,
        kana=audio_query.kana,
    )


def to_model_audio_query(
    fastapi_audio_query: fastapi_model.AudioQuery,
) -> model.AudioQuery:
    return model.AudioQuery(
        accent_phrases=to_model_accent_phrases(fastapi_audio_query.accent_phrases),
        speedScale=fastapi_audio_query.speedScale,
        pitchScale=fastapi_audio_query.pitchScale,
        intonationScale=fastapi_audio_query.intonationScale,
        volumeScale=fastapi_audio_query.volumeScale,
        prePhonemeLength=fastapi_audio_query.prePhonemeLength,
        postPhonemeLength=fastapi_audio_query.postPhonemeLength,
        outputSamplingRate=fastapi_audio_query.outputSamplingRate,
        outputStereo=fastapi_audio_query.outputStereo,
        kana=fastapi_audio_query.kana,
    )


def from_model_speaker_style(
    speaker_style: model.SpeakerStyle,
) -> fastapi_model.SpeakerStyle:
    return fastapi_model.SpeakerStyle(
        name=speaker_style.name,
        id=speaker_style.id,
    )


def to_model_speaker_style(
    fastapi_speaker_style: fastapi_model.SpeakerStyle,
) -> model.SpeakerStyle:
    return model.SpeakerStyle(
        name=fastapi_speaker_style.name,
        id=fastapi_speaker_style.id,
    )


def from_model_speaker(speaker: model.Speaker) -> fastapi_model.Speaker:
    return fastapi_model.Speaker(
        name=speaker.name,
        speaker_uuid=speaker.speaker_uuid,
        styles=speaker.styles,
        version=speaker.version,
    )


def from_model_speakers(speakers: List[model.Speaker]) -> List[fastapi_model.Speaker]:
    return [from_model_speaker(speaker) for speaker in speakers]


def to_model_speaker(fastapi_speaker: fastapi_model.Speaker) -> model.Speaker:
    return model.Speaker(
        name=fastapi_speaker.name,
        speaker_uuid=fastapi_speaker.speaker_uuid,
        styles=fastapi_speaker.styles,
        version=fastapi_speaker.version,
    )


def from_model_style_info(style_info: model.StyleInfo) -> fastapi_model.StyleInfo:
    return fastapi_model.StyleInfo(
        id=style_info.id,
        icon=style_info.icon,
        voice_samples=style_info.voice_samples,
    )


def to_model_style_info(fastapi_style_info: fastapi_model.StyleInfo) -> model.StyleInfo:
    return model.StyleInfo(
        id=fastapi_style_info.id,
        icon=fastapi_style_info.icon,
        voice_samples=fastapi_style_info.voice_samples,
    )


def from_model_speaker_info(
    speaker_info: model.SpeakerInfo,
) -> fastapi_model.SpeakerInfo:
    return fastapi_model.SpeakerInfo(
        policy=speaker_info.policy,
        portrait=speaker_info.portrait,
        style_infos=speaker_info.style_infos,
    )


def to_model_speaker_info(
    fastapi_speaker_info: fastapi_model.SpeakerInfo,
) -> model.SpeakerInfo:
    return model.SpeakerInfo(
        policy=fastapi_speaker_info.policy,
        portrait=fastapi_speaker_info.portrait,
        style_infos=fastapi_speaker_info.style_infos,
    )


def from_model_preset(preset: preset.Preset) -> fastapi_model.Preset:
    return fastapi_model.Preset(
        id=preset.id,
        name=preset.name,
        speaker_uuid=preset.speaker_uuid,
        style_id=preset.style_id,
        speedScale=preset.speedScale,
        pitchScale=preset.pitchScale,
        intonationScale=preset.intonationScale,
        volumeScale=preset.volumeScale,
        prePhonemeLength=preset.prePhonemeLength,
        postPhonemeLength=preset.postPhonemeLength,
    )


def from_model_presets(presets: List[preset.Preset]) -> List[fastapi_model.Preset]:
    return [from_model_preset(preset) for preset in presets]


def to_model_preset(fastapi_preset: fastapi_model.Preset) -> preset.Preset:
    return preset.Preset(
        id=fastapi_preset.id,
        name=fastapi_preset.name,
        speaker_uuid=fastapi_preset.speaker_uuid,
        style_id=fastapi_preset.style_id,
        speedScale=fastapi_preset.speedScale,
        pitchScale=fastapi_preset.pitchScale,
        intonationScale=fastapi_preset.intonationScale,
        volumeScale=fastapi_preset.volumeScale,
        prePhonemeLength=fastapi_preset.prePhonemeLength,
        postPhonemeLength=fastapi_preset.postPhonemeLength,
    )
