import argparse
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import List

try:
    import each_cpp_forwarder
except:
    from voicevox_engine.dev import each_cpp_forwarder

import romkan
import soundfile
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse

from voicevox_engine.full_context_label import extract_full_context_label
from voicevox_engine.model import AccentPhrase, AudioQuery, Mora
from voicevox_engine.synthesis_engine import SynthesisEngine


def mora_to_text(mora: str):
    if mora == "cl":
        return "ッ"
    elif mora == "ti":
        return "ティ"
    elif mora == "tu":
        return "トゥ"
    elif mora == "di":
        return "ディ"
    elif mora == "du":
        return "ドゥ"
    else:
        return romkan.to_katakana(mora)


def generate_app(use_gpu: bool):
    root_dir = Path(__file__).parent

    app = FastAPI()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    each_cpp_forwarder.initialize("1", "2", "3", use_gpu)
    engine = SynthesisEngine(
        yukarin_s_forwarder=each_cpp_forwarder.yukarin_s_forward,
        yukarin_sa_forwarder=each_cpp_forwarder.yukarin_sa_forward,
        decode_forwarder=each_cpp_forwarder.decode_forward,
    )

    def replace_mora_pitch(
        accent_phrases: List[AccentPhrase], speaker_id: int
    ) -> List[AccentPhrase]:
        return engine.extract_phoneme_f0(
            accent_phrases=accent_phrases, speaker_id=speaker_id
        )

    def create_accent_phrases(text: str, speaker_id: int) -> List[AccentPhrase]:
        if len(text.strip()) == 0:
            return []

        utterance = extract_full_context_label(text)
        return replace_mora_pitch(
            accent_phrases=[
                AccentPhrase(
                    moras=[
                        Mora(
                            text=mora_to_text(
                                "".join([p.phoneme for p in mora.phonemes])
                            ),
                            consonant=(
                                mora.consonant.phoneme
                                if mora.consonant is not None
                                else None
                            ),
                            vowel=mora.vowel.phoneme,
                            pitch=0,  # TODO: 設計が汚い
                        )
                        for mora in accent_phrase.moras
                    ],
                    accent=accent_phrase.accent,
                    pause_mora=(
                        Mora(text="、", consonant=None, vowel="pau", pitch=0)
                        if (
                            i_accent_phrase == len(breath_group.accent_phrases) - 1
                            and i_breath_group != len(utterance.breath_groups) - 1
                        )
                        else None
                    ),
                )
                for i_breath_group, breath_group in enumerate(utterance.breath_groups)
                for i_accent_phrase, accent_phrase in enumerate(
                    breath_group.accent_phrases
                )
            ],
            speaker_id=speaker_id,
        )

    @app.post("/accent_phrases", response_model=List[AccentPhrase])
    def accent_phrases(text: str, speaker: int):
        return create_accent_phrases(text, speaker_id=speaker)

    @app.post("/mora_pitch", response_model=List[AccentPhrase])
    def mora_pitch(accent_phrases: List[AccentPhrase], speaker: int):
        return replace_mora_pitch(accent_phrases, speaker_id=speaker)

    @app.post("/audio_query", response_model=AudioQuery)
    def audio_query(text: str, speaker: int):
        return AudioQuery(
            accent_phrases=create_accent_phrases(text, speaker_id=speaker),
            speedScale=1,
            pitchScale=0,
            intonationScale=1,
        )

    @app.get("/version")
    def version() -> str:
        return (root_dir / "VERSION.txt").read_text()

    @app.post(
        "/synthesis",
        response_class=FileResponse,
        responses={
            200: {
                "content": {
                    "audio/wav": {"schema": {"type": "string", "format": "binary"}}
                },
            }
        },
    )
    def synthesis(query: AudioQuery, speaker: int):
        # StreamResponseだとnuiktaビルド後の実行でエラーが発生するのでFileResponse
        wave = engine.synthesis(query=query, speaker_id=speaker)
        sr = 24000

        with NamedTemporaryFile(delete=False) as f:
            soundfile.write(file=f, data=wave, samplerate=sr, format="WAV")

        return FileResponse(f.name, media_type="audio/wav")

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=50021)
    parser.add_argument("--use_gpu", action="store_true")
    args = parser.parse_args()
    uvicorn.run(generate_app(use_gpu=args.use_gpu), host=args.host, port=args.port)
