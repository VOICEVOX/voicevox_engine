import argparse
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import List, Optional

import numpy as np
import resampy
import soundfile
import uvicorn
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse

from voicevox_engine.full_context_label import extract_full_context_label
from voicevox_engine.model import AccentPhrase, AudioQuery, Mora, Speaker
from voicevox_engine.mora_list import openjtalk_mora2text
from voicevox_engine.synthesis_engine import SynthesisEngine


def make_synthesis_engine(
    use_gpu: bool,
    voicevox_dir: Optional[Path] = None,
    voicelib_dir: Optional[Path] = None,
) -> SynthesisEngine:
    """
    音声ライブラリをロードして、音声合成エンジンを生成

    Parameters
    ----------
    use_gpu: bool
        音声ライブラリに GPU を使わせるか否か
    voicevox_dir: Path, optional, default=None
        音声ライブラリの Python モジュールがあるディレクトリ
        None のとき、Python 標準のモジュール検索パスのどれかにあるとする
    voicelib_dir: Path, optional, default=None
        音声ライブラリ自体があるディレクトリ
        None のとき、音声ライブラリの Python モジュールと同じディレクトリにあるとする
    """

    # Python モジュール検索パスへ追加
    if voicevox_dir is not None:
        print("Notice: --voicevox_dir is " + voicevox_dir.as_posix(), file=sys.stderr)
        if voicevox_dir.exists():
            sys.path.insert(0, str(voicevox_dir))

    try:
        import each_cpp_forwarder
    except ImportError:
        from voicevox_engine.dev import each_cpp_forwarder

        # 音声ライブラリの Python モジュールをロードできなかった
        print(
            "Notice: mock-library will be used. Try re-run with valid --voicevox_dir",  # noqa
            file=sys.stderr,
        )

    if voicelib_dir is None:
        voicelib_dir = Path(each_cpp_forwarder.__file__).parent

    each_cpp_forwarder.initialize(
        voicelib_dir.as_posix() + "/",
        "1",
        "2",
        "3",
        use_gpu,
    )

    return SynthesisEngine(
        yukarin_s_forwarder=each_cpp_forwarder.yukarin_s_forward,
        yukarin_sa_forwarder=each_cpp_forwarder.yukarin_sa_forward,
        decode_forwarder=each_cpp_forwarder.decode_forward,
    )


def mora_to_text(mora: str):
    if mora in openjtalk_mora2text:
        return openjtalk_mora2text[mora]
    else:
        return mora


def generate_app(engine: SynthesisEngine) -> FastAPI:
    root_dir = Path(__file__).parent
    default_sampling_rate = 24000

    app = FastAPI(
        title="VOICEVOX ENGINE",
        description="VOICEVOXの音声合成エンジンです。",
        version=(root_dir / "VERSION.txt").read_text(),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def replace_mora_data(
        accent_phrases: List[AccentPhrase], speaker_id: int
    ) -> List[AccentPhrase]:
        return engine.replace_mora_pitch(
            accent_phrases=engine.replace_phoneme_length(
                accent_phrases=accent_phrases,
                speaker_id=speaker_id,
            ),
            speaker_id=speaker_id,
        )

    def create_accent_phrases(text: str, speaker_id: int) -> List[AccentPhrase]:
        if len(text.strip()) == 0:
            return []

        utterance = extract_full_context_label(text)
        return replace_mora_data(
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
                            consonant_length=0 if mora.consonant is not None else None,
                            vowel=mora.vowel.phoneme,
                            vowel_length=0,
                            pitch=0,
                        )
                        for mora in accent_phrase.moras
                    ],
                    accent=accent_phrase.accent,
                    pause_mora=(
                        Mora(
                            text="、",
                            consonant=None,
                            consonant_length=None,
                            vowel="pau",
                            vowel_length=0,
                            pitch=0,
                        )
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

    @app.post(
        "/audio_query",
        response_model=AudioQuery,
        tags=["クエリ作成"],
        summary="音声合成用のクエリを作成する",
    )
    def audio_query(text: str, speaker: int):
        """
        クエリの初期値を得ます。ここで得られたクエリはそのまま音声合成に利用できます。各値の意味は`Schemas`を参照してください。
        """
        return AudioQuery(
            accent_phrases=create_accent_phrases(text, speaker_id=speaker),
            speedScale=1,
            pitchScale=0,
            intonationScale=1,
            volumeScale=1,
            prePhonemeLength=0.1,
            postPhonemeLength=0.1,
            outputSamplingRate=default_sampling_rate,
            outputStereo=False,
        )

    @app.post(
        "/accent_phrases",
        response_model=List[AccentPhrase],
        tags=["クエリ編集"],
        summary="テキストからアクセント句を得る",
    )
    def accent_phrases(text: str, speaker: int):
        return create_accent_phrases(text, speaker_id=speaker)

    @app.post(
        "/mora_data",
        response_model=List[AccentPhrase],
        tags=["クエリ編集"],
        summary="アクセント句から音高・音素長を得る",
    )
    def mora_data(accent_phrases: List[AccentPhrase], speaker: int):
        return replace_mora_data(accent_phrases, speaker_id=speaker)

    @app.post(
        "/mora_length",
        response_model=List[AccentPhrase],
        tags=["クエリ編集"],
        summary="アクセント句から音素長を得る",
    )
    def mora_length(accent_phrases: List[AccentPhrase], speaker: int):
        return engine.replace_phoneme_length(
            accent_phrases=accent_phrases, speaker_id=speaker
        )

    @app.post(
        "/mora_pitch",
        response_model=List[AccentPhrase],
        tags=["クエリ編集"],
        summary="アクセント句から音高を得る",
    )
    def mora_pitch(accent_phrases: List[AccentPhrase], speaker: int):
        return engine.replace_mora_pitch(
            accent_phrases=accent_phrases, speaker_id=speaker
        )

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
        tags=["音声合成"],
        summary="音声合成する",
    )
    def synthesis(query: AudioQuery, speaker: int):
        # StreamResponseだとnuiktaビルド後の実行でエラーが発生するのでFileResponse
        wave = engine.synthesis(query=query, speaker_id=speaker)

        # サンプリングレートの変更
        if query.outputSamplingRate != default_sampling_rate:
            wave = resampy.resample(
                wave,
                default_sampling_rate,
                query.outputSamplingRate,
                filter="kaiser_fast",
            )

        # ステレオ変換
        if query.outputStereo:
            wave = np.array([wave, wave]).T

        with NamedTemporaryFile(delete=False) as f:
            soundfile.write(
                file=f, data=wave, samplerate=query.outputSamplingRate, format="WAV"
            )

        return FileResponse(f.name, media_type="audio/wav")

    @app.get("/version", tags=["その他"])
    def version() -> str:
        return (root_dir / "VERSION.txt").read_text()

    @app.get("/speakers", response_model=List[Speaker], tags=["その他"])
    def speakers():
        # TODO 音声ライブラリのAPIが出来たら差し替える
        return Response(
            content=(root_dir / "speakers.json").read_text("utf-8"),
            media_type="application/json",
        )

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=50021)
    parser.add_argument("--use_gpu", action="store_true")
    parser.add_argument("--voicevox_dir", type=Path, default=None)
    parser.add_argument("--voicelib_dir", type=Path, default=None)
    args = parser.parse_args()
    uvicorn.run(
        generate_app(
            make_synthesis_engine(
                use_gpu=args.use_gpu,
                voicevox_dir=args.voicevox_dir,
                voicelib_dir=args.voicelib_dir,
            )
        ),
        host=args.host,
        port=args.port,
    )
