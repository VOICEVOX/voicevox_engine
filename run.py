import argparse
import asyncio
import base64
import json
import multiprocessing
import zipfile
from functools import lru_cache
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryFile
from typing import List, Optional

import soundfile
import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.params import Query
from starlette.responses import FileResponse

from voicevox_engine import model
from voicevox_engine.cancellable_engine import CancellableEngine
from voicevox_engine.kana_parser import create_kana, parse_kana
from voicevox_engine.model import ParseKanaError
from voicevox_engine.morphing import synthesis_morphing
from voicevox_engine.morphing import (
    synthesis_morphing_parameter as _synthesis_morphing_parameter,
)
from voicevox_engine.preset import PresetLoader
from voicevox_engine.synthesis_engine import SynthesisEngineBase, make_synthesis_engine
from voicevox_engine.synthesis_engine.synthesis_engine_base import (
    adjust_interrogative_accent_phrases,
)
from voicevox_engine.utility import ConnectBase64WavesException, connect_base64_waves
from voicevox_engine.webapi.fastapi_model import (
    AccentPhrase,
    AudioQuery,
    ParseKanaBadRequest,
    Preset,
    Speaker,
    SpeakerInfo,
)

"""
voicevox_enbine/model.pyで定義されている型は内部で使用する方なので、リクエスト及びレスポンスを行う際に使用してはならない。
リクエスト・レスポンスで使用する型はvoicevox_engine/webapi/fastapi_model.pyで定義されている型を使用し、
内部で使用している型から(or に)変換すること
"""


def b64encode_str(s):
    return base64.b64encode(s).decode("utf-8")


def generate_app(engine: SynthesisEngineBase) -> FastAPI:
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

    preset_loader = PresetLoader(
        preset_path=root_dir / "presets.yaml",
    )

    # キャッシュを有効化
    # モジュール側でlru_cacheを指定するとキャッシュを制御しにくいため、HTTPサーバ側で指定する
    # TODO: キャッシュを管理するモジュール側API・HTTP側APIを用意する
    synthesis_morphing_parameter = lru_cache(maxsize=4)(_synthesis_morphing_parameter)

    @app.on_event("startup")
    async def start_catch_disconnection():
        if args.enable_cancellable_synthesis:
            loop = asyncio.get_event_loop()
            _ = loop.create_task(cancellable_engine.catch_disconnection())

    def enable_interrogative_query_param() -> Query:
        return Query(
            default=True,
            description="疑問系のテキストが与えられたら自動調整する機能を有効にする。現在は長音を付け足すことで擬似的に実装される",
        )

    @app.post(
        "/audio_query",
        response_model=AudioQuery,
        tags=["クエリ作成"],
        summary="音声合成用のクエリを作成する",
    )
    def audio_query(
        text: str,
        speaker: int,
        enable_interrogative: bool = enable_interrogative_query_param(),  # noqa B008,
    ) -> AudioQuery:
        """
        クエリの初期値を得ます。ここで得られたクエリはそのまま音声合成に利用できます。各値の意味は`Schemas`を参照してください。
        """
        accent_phrases = engine.create_accent_phrases(
            text,
            speaker_id=speaker,
            enable_interrogative=enable_interrogative,
        )
        return AudioQuery.from_engine(
            model.AudioQuery(
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
        )

    @app.post(
        "/audio_query_from_preset",
        response_model=AudioQuery,
        tags=["クエリ作成"],
        summary="音声合成用のクエリをプリセットを用いて作成する",
    )
    def audio_query_from_preset(
        text: str,
        preset_id: int,
        enable_interrogative: bool = enable_interrogative_query_param(),  # noqa B008,
    ) -> AudioQuery:
        """
        クエリの初期値を得ます。ここで得られたクエリはそのまま音声合成に利用できます。各値の意味は`Schemas`を参照してください。
        """
        presets, err_detail = preset_loader.load_presets()
        if err_detail:
            raise HTTPException(status_code=422, detail=err_detail)
        for preset in presets:
            if preset.id == preset_id:
                selected_preset = preset
                break
        else:
            raise HTTPException(status_code=422, detail="該当するプリセットIDが見つかりません")

        accent_phrases = engine.create_accent_phrases(
            text,
            speaker_id=selected_preset.style_id,
            enable_interrogative=enable_interrogative,
        )
        return AudioQuery.from_engine(
            model.AudioQuery(
                accent_phrases=accent_phrases,
                speedScale=selected_preset.speedScale,
                pitchScale=selected_preset.pitchScale,
                intonationScale=selected_preset.intonationScale,
                volumeScale=selected_preset.volumeScale,
                prePhonemeLength=selected_preset.prePhonemeLength,
                postPhonemeLength=selected_preset.postPhonemeLength,
                outputSamplingRate=default_sampling_rate,
                outputStereo=False,
                kana=create_kana(accent_phrases),
            )
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
    def accent_phrases(
        text: str,
        speaker: int,
        is_kana: bool = False,
        enable_interrogative: bool = enable_interrogative_query_param(),  # noqa B008,
    ) -> List[AccentPhrase]:
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
                accent_phrases, interrogative_accent_phrase_marks = parse_kana(
                    text, enable_interrogative
                )
            except ParseKanaError as err:
                raise HTTPException(
                    status_code=400,
                    detail=ParseKanaBadRequest(err).dict(),
                )
            accent_phrases = engine.replace_mora_data(
                accent_phrases=accent_phrases, speaker_id=speaker
            )

            return [
                AccentPhrase.from_engine(accent_phrase)
                for accent_phrase in (
                    adjust_interrogative_accent_phrases(
                        accent_phrases,
                        interrogative_accent_phrase_marks,
                        enable_interrogative,
                    )
                )
            ]
        else:
            return [
                AccentPhrase.from_engine(accent_phrase)
                for accent_phrase in (
                    engine.create_accent_phrases(
                        text,
                        speaker_id=speaker,
                        enable_interrogative=enable_interrogative,
                    )
                )
            ]

    @app.post(
        "/mora_data",
        response_model=List[AccentPhrase],
        tags=["クエリ編集"],
        summary="アクセント句から音高・音素長を得る",
    )
    def mora_data(
        accent_phrases: List[AccentPhrase], speaker: int
    ) -> List[AccentPhrase]:
        return [
            AccentPhrase.from_engine(accent_phrase)
            for accent_phrase in (
                engine.replace_mora_data(
                    accent_phrases=[
                        accent_phrase.to_engine() for accent_phrase in accent_phrases
                    ],
                    speaker_id=speaker,
                )
            )
        ]

    @app.post(
        "/mora_length",
        response_model=List[AccentPhrase],
        tags=["クエリ編集"],
        summary="アクセント句から音素長を得る",
    )
    def mora_length(
        accent_phrases: List[AccentPhrase], speaker: int
    ) -> List[AccentPhrase]:
        return [
            AccentPhrase.from_engine(accent_phrase)
            for accent_phrase in (
                engine.replace_phoneme_length(
                    accent_phrases=[
                        accent_phrase.to_engine() for accent_phrase in accent_phrases
                    ],
                    speaker_id=speaker,
                )
            )
        ]

    @app.post(
        "/mora_pitch",
        response_model=List[AccentPhrase],
        tags=["クエリ編集"],
        summary="アクセント句から音高を得る",
    )
    def mora_pitch(
        accent_phrases: List[AccentPhrase], speaker: int
    ) -> List[AccentPhrase]:
        return [
            AccentPhrase.from_engine(accent_phrase)
            for accent_phrase in (
                engine.replace_mora_pitch(
                    accent_phrases=[
                        accent_phrase.to_engine() for accent_phrase in accent_phrases
                    ],
                    speaker_id=speaker,
                )
            )
        ]

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
    def synthesis(query: AudioQuery, speaker: int) -> FileResponse:
        wave = engine.synthesis(
            query=query.to_engine(),
            speaker_id=speaker,
        )

        with NamedTemporaryFile(delete=False) as f:
            soundfile.write(
                file=f, data=wave, samplerate=query.outputSamplingRate, format="WAV"
            )

        return FileResponse(f.name, media_type="audio/wav")

    @app.post(
        "/cancellable_synthesis",
        response_class=FileResponse,
        responses={
            200: {
                "content": {
                    "audio/wav": {"schema": {"type": "string", "format": "binary"}}
                },
            }
        },
        tags=["音声合成"],
        summary="音声合成する（キャンセル可能）",
    )
    def cancellable_synthesis(
        query: AudioQuery, speaker: int, request: Request
    ) -> FileResponse:
        if not args.enable_cancellable_synthesis:
            raise HTTPException(
                status_code=404,
                detail="実験的機能はデフォルトで無効になっています。使用するには引数を指定してください。",
            )
        f_name = cancellable_engine.synthesis(
            query=query.to_engine(),
            speaker_id=speaker,
            request=request,
        )

        return FileResponse(f_name, media_type="audio/wav")

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
    def multi_synthesis(queries: List[AudioQuery], speaker: int) -> FileResponse:
        sampling_rate = queries[0].outputSamplingRate

        with NamedTemporaryFile(delete=False) as f:

            with zipfile.ZipFile(f, mode="a") as zip_file:

                for i in range(len(queries)):

                    if queries[i].outputSamplingRate != sampling_rate:
                        raise HTTPException(
                            status_code=422, detail="サンプリングレートが異なるクエリがあります"
                        )

                    with TemporaryFile() as wav_file:

                        wave = engine.synthesis(
                            query=queries[i].to_engine(),
                            speaker_id=speaker,
                        )
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
        "/synthesis_morphing",
        response_class=FileResponse,
        responses={
            200: {
                "content": {
                    "audio/wav": {"schema": {"type": "string", "format": "binary"}}
                },
            }
        },
        tags=["音声合成"],
        summary="2人の話者でモーフィングした音声を合成する",
    )
    def _synthesis_morphing(
        query: AudioQuery,
        base_speaker: int,
        target_speaker: int,
        morph_rate: float = Query(..., ge=0.0, le=1.0),  # noqa: B008
    ) -> FileResponse:
        """
        指定された2人の話者で音声を合成、指定した割合でモーフィングした音声を得ます。
        モーフィングの割合は`morph_rate`で指定でき、0.0でベースの話者、1.0でターゲットの話者に近づきます。
        """

        # 生成したパラメータはキャッシュされる
        morph_param = synthesis_morphing_parameter(
            engine=engine,
            query=query.to_engine(),
            base_speaker=base_speaker,
            target_speaker=target_speaker,
        )

        morph_wave = synthesis_morphing(
            morph_param=morph_param,
            morph_rate=morph_rate,
            output_stereo=query.outputStereo,
        )

        with NamedTemporaryFile(delete=False) as f:
            soundfile.write(
                file=f,
                data=morph_wave,
                samplerate=morph_param.fs,
                format="WAV",
            )

        return FileResponse(f.name, media_type="audio/wav")

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
        summary="base64エンコードされた複数のwavデータを一つに結合する",
    )
    def connect_waves(waves: List[str]) -> FileResponse:
        """
        base64エンコードされたwavデータを一纏めにし、wavファイルで返します。
        """
        try:
            waves_nparray, sampling_rate = connect_base64_waves(waves)
        except ConnectBase64WavesException as err:
            raise HTTPException(status_code=422, detail=str(err))

        with NamedTemporaryFile(delete=False) as f:
            soundfile.write(
                file=f,
                data=waves_nparray,
                samplerate=sampling_rate,
                format="WAV",
            )

            return FileResponse(f.name, media_type="audio/wav")

    @app.get("/presets", response_model=List[Preset], tags=["その他"])
    def get_presets() -> List[Preset]:
        """
        エンジンが保持しているプリセットの設定を返します

        Returns
        -------
        presets: List[Preset]
            プリセットのリスト
        """
        presets, err_detail = preset_loader.load_presets()
        if err_detail:
            raise HTTPException(status_code=422, detail=err_detail)
        return [preset.to_engine() for preset in presets]

    @app.get("/version", tags=["その他"])
    def version() -> str:
        return (root_dir / "VERSION.txt").read_text()

    @app.get("/speakers", response_model=List[Speaker], tags=["その他"])
    def speakers() -> Response:
        return Response(
            content=engine.speakers,
            media_type="application/json",
        )

    @app.get("/speaker_info", response_model=SpeakerInfo, tags=["その他"])
    def speaker_info(speaker_uuid: str) -> SpeakerInfo:
        """
        指定されたspeaker_uuidに関する情報をjson形式で返します。
        画像や音声はbase64エンコードされたものが返されます。

        Returns
        -------
        ret_data: SpeakerInfo
        """
        speakers = json.loads(engine.speakers)
        for i in range(len(speakers)):
            if speakers[i]["speaker_uuid"] == speaker_uuid:
                speaker = speakers[i]
                break
        else:
            raise HTTPException(status_code=404, detail="該当する話者が見つかりません")

        try:
            policy = Path(f"speaker_info/{speaker_uuid}/policy.md").read_text("utf-8")
            portrait = b64encode_str(
                Path(f"speaker_info/{speaker_uuid}/portrait.png").read_bytes()
            )
            style_infos = []
            for style in speaker["styles"]:
                id = style["id"]
                icon = b64encode_str(
                    Path(f"speaker_info/{speaker_uuid}/icons/{id}.png").read_bytes()
                )
                voice_samples = [
                    b64encode_str(
                        Path(
                            "speaker_info/{}/voice_samples/{}_{}.wav".format(
                                speaker_uuid, id, str(j + 1).zfill(3)
                            )
                        ).read_bytes()
                    )
                    for j in range(3)
                ]
                style_infos.append(
                    model.StyleInfo(id=id, icon=icon, voice_samples=voice_samples)
                )
        except FileNotFoundError:
            import traceback

            traceback.print_exc()
            raise HTTPException(status_code=500, detail="追加情報が見つかりませんでした")

        return SpeakerInfo.from_engine(
            model.SpeakerInfo(policy=policy, portrait=portrait, style_infos=style_infos)
        )

    return app


if __name__ == "__main__":
    multiprocessing.freeze_support()
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=50021)
    parser.add_argument("--use_gpu", action="store_true")
    parser.add_argument("--voicevox_dir", type=Path, default=None)
    parser.add_argument("--voicelib_dir", type=Path, default=None)
    parser.add_argument("--enable_cancellable_synthesis", action="store_true")
    parser.add_argument("--init_processes", type=int, default=2)
    args = parser.parse_args()

    # voicelib_dir が Noneのとき、音声ライブラリの Python モジュールと同じディレクトリにあるとする
    voicelib_dir: Optional[Path] = args.voicelib_dir
    if voicelib_dir is None:
        if args.voicevox_dir is not None:
            voicelib_dir = args.voicevox_dir
        else:
            voicelib_dir = Path(__file__).parent  # core.__file__だとnuitkaビルド後にエラー

    cancellable_engine = None
    if args.enable_cancellable_synthesis:
        cancellable_engine = CancellableEngine(args, voicelib_dir)

    uvicorn.run(
        generate_app(
            make_synthesis_engine(
                use_gpu=args.use_gpu,
                voicelib_dir=voicelib_dir,
                voicevox_dir=args.voicevox_dir,
            )
        ),
        host=args.host,
        port=args.port,
    )
