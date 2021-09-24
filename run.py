import argparse
import base64
import io
import sys
import zipfile
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryFile
from typing import List, Optional

import soundfile
import uvicorn
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from numpy import concatenate
from starlette.responses import FileResponse

from voicevox_engine.full_context_label import extract_full_context_label
from voicevox_engine.kana_parser import create_kana, parse_kana
from voicevox_engine.model import (
    AccentPhrase,
    AudioQuery,
    Mora,
    ParseKanaBadRequest,
    ParseKanaError,
    Speaker,
)
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

    has_voicevox_core = True
    try:
        import core
    except ImportError:
        import traceback

        from voicevox_engine.dev import core

        has_voicevox_core = False

        # 音声ライブラリの Python モジュールをロードできなかった
        traceback.print_exc()
        print(
            "Notice: mock-library will be used. Try re-run with valid --voicevox_dir",  # noqa
            file=sys.stderr,
        )

    if voicelib_dir is None:
        voicelib_dir = Path(__file__).parent  # core.__file__だとnuitkaビルド後にエラー

    core.initialize(voicelib_dir.as_posix() + "/", use_gpu)

    if has_voicevox_core:
        return SynthesisEngine(
            yukarin_s_forwarder=core.yukarin_s_forward,
            yukarin_sa_forwarder=core.yukarin_sa_forward,
            decode_forwarder=core.decode_forward,
            speakers=core.metas(),
        )

    from voicevox_engine.dev.synthesis_engine import (
        SynthesisEngine as mock_synthesis_engine,
    )

    # モックで置き換える
    return mock_synthesis_engine()


def mora_to_text(mora: str):
    if mora[-1:] in ["A", "I", "U", "E", "O"]:
        # 無声化母音を小文字に
        mora = mora[:-1] + mora[-1].lower()
    if mora in openjtalk_mora2text:
        return openjtalk_mora2text[mora]
    else:
        return mora


def generate_app(engine: SynthesisEngine) -> FastAPI:
    root_dir = Path(__file__).parent

    default_sampling_rate = engine.default_sampling_rate

    app = FastAPI(
        title="VOICEVOX ENGINE",
        description="VOICEVOXの音声合成エンジンです。",
        version=(root_dir / "VERSION.txt").read_text().strip(),
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
        if len(utterance.breath_groups) == 0:
            return []

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
        accent_phrases = create_accent_phrases(text, speaker_id=speaker)
        return AudioQuery(
            accent_phrases=accent_phrases,
            speedScale=1,
            pitchScale=0,
            intonationScale=1,
            volumeScale=1,
            prePhonemeLength=0.1,
            postPhonemeLength=0.1,
            outputSamplingRate=default_sampling_rate,
            outputStereo=False,
            kana=create_kana(accent_phrases),
        )

    @app.post(
        "/accent_phrases",
        response_model=List[AccentPhrase],
        tags=["クエリ編集"],
        summary="テキストからアクセント句を得る",
        responses={
            400: {
                "description": "読み仮名のパースに失敗",
                "model": ParseKanaBadRequest,
            }
        },
    )
    def accent_phrases(text: str, speaker: int, is_kana: bool = False):
        """
        テキストからアクセント句を得ます。
        is_kanaが`true`のとき、テキストは次のようなAquesTalkライクな記法に従う読み仮名として処理されます。デフォルトは`false`です。
        * 全てのカナはカタカナで記述される
        * アクセント句は`/`または`、`で区切る。`、`で区切った場合に限り無音区間が挿入される。
        * カナの手前に`_`を入れるとそのカナは無声化される
        * アクセント位置を`'`で指定する。全てのアクセント句にはアクセント位置を1つ指定する必要がある。
        """
        if is_kana:
            try:
                accent_phrases = parse_kana(text)
            except ParseKanaError as err:
                raise HTTPException(
                    status_code=400,
                    detail=ParseKanaBadRequest(err).dict(),
                )
            return replace_mora_data(accent_phrases=accent_phrases, speaker_id=speaker)
        else:
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
        wave = engine.synthesis(query=query, speaker_id=speaker)

        with NamedTemporaryFile(delete=False) as f:
            soundfile.write(
                file=f, data=wave, samplerate=query.outputSamplingRate, format="WAV"
            )

        return FileResponse(f.name, media_type="audio/wav")

    @app.post(
        "/multi_synthesis",
        response_class=FileResponse,
        responses={
            200: {
                "content": {
                    "application/zip": {
                        "schema": {"type": "string", "format": "binary"}
                    }
                },
            }
        },
        tags=["音声合成"],
        summary="複数まとめて音声合成する",
    )
    def multi_synthesis(queries: List[AudioQuery], speaker: int):
        sampling_rate = queries[0].outputSamplingRate

        with NamedTemporaryFile(delete=False) as f:

            with zipfile.ZipFile(f, mode="a") as zip_file:

                for i in range(len(queries)):

                    if queries[i].outputSamplingRate != sampling_rate:
                        raise HTTPException(
                            status_code=422, detail="サンプリングレートが異なるクエリがあります"
                        )

                    with TemporaryFile() as wav_file:

                        wave = engine.synthesis(query=queries[i], speaker_id=speaker)
                        soundfile.write(
                            file=wav_file,
                            data=wave,
                            samplerate=sampling_rate,
                            format="WAV",
                        )
                        wav_file.seek(0)
                        zip_file.writestr(f"{str(i+1).zfill(3)}.wav", wav_file.read())

        return FileResponse(f.name, media_type="application/zip")

    @app.post(
        "/connect_waves",
        response_class=FileResponse,
        responses={
            200: {
                "content": {
                    "audio/wav": {"schema": {"type": "string", "format": "binary"}}
                },
            }
        },
        tags=["その他"],
        summary="複数の音声を一つに結合する",
    )
    def connect_waves(waves: List[str]):
        """
        base64エンコードされたwavデータを一纏めにし、wavファイルで返します。
        """
        waves_nparray = []
        for i in range(len(waves)):
            try:
                wav_bin = base64.standard_b64decode(waves[i])
            except ValueError:
                raise HTTPException(status_code=422, detail="base64デコードに失敗しました")
            try:
                _data, _sampling_rate = soundfile.read(io.BytesIO(wav_bin))
            except Exception:
                raise HTTPException(status_code=422, detail="wavファイルを読み込めませんでした")
            if i == 0:
                sampling_rate = _sampling_rate
            else:
                if sampling_rate != _sampling_rate:
                    raise HTTPException(status_code=422, detail="ファイル間でサンプリングレートが異なります")
            waves_nparray.append(_data)

        with NamedTemporaryFile(delete=False) as f:
            soundfile.write(
                file=f,
                data=concatenate(waves_nparray),
                samplerate=sampling_rate,
                format="WAV",
            )

            return FileResponse(f.name, media_type="audio/wav")

    @app.get("/version", tags=["その他"])
    def version() -> str:
        return (root_dir / "VERSION.txt").read_text()

    @app.get("/speakers", response_model=List[Speaker], tags=["その他"])
    def speakers():
        return Response(
            content=engine.speakers,
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
