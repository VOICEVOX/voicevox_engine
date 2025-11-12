"""Forced Alignによる音声と発音を自動調整機能(Guide)を提供するAPI Router"""

import io
import json
from typing import Annotated

import numpy as np
import pyworld as pw
import soundfile
import soxr
from fastapi import APIRouter, File, Form, UploadFile
from snfa import Aligner, trim_audio
from snfa.viterbi import Segment

from voicevox_engine.model import AudioQuery
from voicevox_engine.tts_pipeline.tts_engine import (
    _to_flatten_phonemes,
    to_flatten_moras,
)

F0_EPSILON = 0.1
DUR_EPSILON = 0.02


def _seg_dur(seg: Segment) -> float:
    return float((seg.end - seg.start) / 1000.0)


def _sanitize_long_vowel(segs: list[Segment]) -> list[Segment]:
    """Sanitize long vowels (e.g. `s-o-o`, `y-u-u`) by dividing their duration evenly."""
    for i in range(len(segs) - 1):
        if segs[i].phoneme == segs[i + 1].phoneme:
            mid = int((segs[i].start + segs[i + 1].end) / 2)
            segs[i].end = mid
            segs[i + 1].start = mid + 1
    return segs


def generate_guide_router() -> APIRouter:
    """Guide API Router を生成する"""
    router = APIRouter(tags=["クエリ編集"])
    aligner = Aligner()

    @router.post(
        "/guide",
        summary="参考音声に合わせて発音タイミングとイントネーションを自動調整したAudioQueryを返します",
    )
    def guide(
        query: Annotated[str, Form(...)],
        ref_audio: Annotated[UploadFile, File(...)],
        normalize: Annotated[bool, Form(...)] = True,
        trim: Annotated[bool, Form(...)] = True,
        assign_length: Annotated[bool, Form(...)] = True,
        assign_pitch: Annotated[bool, Form(...)] = True,
    ) -> AudioQuery:
        # Load AudioQuery and audio file
        query_obj = AudioQuery(**json.loads(query))
        file_bytes = ref_audio.file.read()
        wav, sr = soundfile.read(io.BytesIO(file_bytes))

        # Convert stereo to mono if necessary
        if wav.ndim == 2:
            wav = wav.mean(axis=1 if wav.shape[1] == 2 else 0)

        # Optionally trim silence
        if trim:
            wav, _ = trim_audio(wav, top_db=30)

        # Resample to match aligner's sampling rate
        r_wav = (
            soxr.resample(wav, sr, aligner.sr, quality="HQ")
            if sr != aligner.sr
            else wav
        )

        # Flatten phonemes
        phonemes = [
            p._phoneme.lower()
            for p in _to_flatten_phonemes(to_flatten_moras(query_obj.accent_phrases))
        ]

        # Forced alignment
        segs = aligner(r_wav, phonemes)[1:-1]  # Trim start & end pause
        segs = _sanitize_long_vowel(segs)

        # F0 extraction (use original waveform for better resolution)
        f0, _ = pw.harvest(wav.astype(np.double), sr, frame_period=5.0)
        f0 = np.log(f0 + 1e-5)
        f0 = np.clip(f0, 0.0, 6.5)
        scale_factor = f0.shape[0] / (r_wav.shape[0] / aligner.sr * 1000)

        # Pitch normalization
        drift = 0.0
        if normalize:
            moras = to_flatten_moras(query_obj.accent_phrases)
            pd_list = [
                (
                    mora.pitch,
                    mora.vowel_length + (mora.consonant_length or 0.0),
                )
                for mora in moras
                if mora.pitch > F0_EPSILON
            ]
            src_pitch = sum(p * d for p, d in pd_list) / sum(d for _, d in pd_list)
            new_pitch = np.mean(f0[f0 > F0_EPSILON])
            drift = src_pitch - new_pitch

        # Assign segment durations and pitch
        ap_idx = mora_idx = seg_idx = 0
        while ap_idx < len(query_obj.accent_phrases):
            ap = query_obj.accent_phrases[ap_idx]
            mora = ap.moras[mora_idx]
            if mora.consonant and mora.consonant_length:
                assert mora.consonant.lower() == segs[seg_idx].phoneme
                assert mora.vowel.lower() == segs[seg_idx + 1].phoneme
                if assign_length:
                    mora.consonant_length = _seg_dur(segs[seg_idx])
                    mora.vowel_length = _seg_dur(segs[seg_idx + 1])
                s, e = segs[seg_idx].start, segs[seg_idx + 1].end
                seg_idx += 2

                # Extend overly short consonants
                if assign_length and (
                    mora.consonant_length <= DUR_EPSILON
                    and mora.vowel_length > 3 * DUR_EPSILON
                ):
                    dur = mora.consonant_length + mora.vowel_length
                    mora.consonant_length = 0.25 * dur
                    mora.vowel_length = 0.75 * dur
            else:
                assert mora.vowel.lower() == segs[seg_idx].phoneme
                if assign_length:
                    mora.vowel_length = _seg_dur(segs[seg_idx])
                s, e = segs[seg_idx].start, segs[seg_idx].end
                seg_idx += 1
            if assign_pitch:
                # Assign pitch (except for unvoiced vowels)
                if mora.vowel not in ["U", "I", "N", "cl"]:
                    mora_f0 = f0[int(s * scale_factor) : int(e * scale_factor)]
                    mora_f0 = mora_f0[mora_f0 > F0_EPSILON]
                    mora.pitch = (
                        float(np.mean(mora_f0)) + drift if mora_f0.size > 0 else 0.0
                    )

            mora_idx += 1
            if mora_idx == len(ap.moras):
                if ap.pause_mora:
                    assert segs[seg_idx].phoneme == "pau"
                    if assign_length:
                        ap.pause_mora.vowel_length = _seg_dur(segs[seg_idx])
                    seg_idx += 1
                mora_idx = 0
                ap_idx += 1

        return query_obj

    return router
