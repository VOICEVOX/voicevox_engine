import argparse
import asyncio
import base64
import json
import multiprocessing
import os
import re
import sys
import traceback
import zipfile
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from functools import lru_cache
from io import BytesIO, TextIOWrapper
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryFile
from typing import Annotated, Any, Literal, Optional

import soundfile
import uvicorn
from fastapi import Body, Depends, FastAPI, Form, HTTPException
from fastapi import Path as FAPath
from fastapi import Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError, parse_obj_as
from starlette.background import BackgroundTask
from starlette.middleware.errors import ServerErrorMiddleware
from starlette.responses import FileResponse

from voicevox_engine import __version__
from voicevox_engine.cancellable_engine import CancellableEngine
from voicevox_engine.core.core_adapter import CoreAdapter
from voicevox_engine.core.core_initializer import initialize_cores
from voicevox_engine.engine_manifest.EngineManifest import EngineManifest
from voicevox_engine.engine_manifest.EngineManifestLoader import EngineManifestLoader
from voicevox_engine.library_manager import LibraryManager
from voicevox_engine.metas.Metas import StyleId
from voicevox_engine.metas.MetasStore import (
    MetasStore,
    construct_lookup,
    filter_speakers_and_styles,
)
from voicevox_engine.model import (
    AccentPhrase,
    AudioQuery,
    BaseLibraryInfo,
    DownloadableLibraryInfo,
    FrameAudioQuery,
    InstalledLibraryInfo,
    MorphableTargetInfo,
    ParseKanaBadRequest,
    ParseKanaError,
    Score,
    Speaker,
    SpeakerInfo,
    StyleIdNotFoundError,
    SupportedDevicesInfo,
    UserDictWord,
    VvlibManifest,
    WordTypes,
)
from voicevox_engine.morphing import (
    get_morphable_targets,
    is_synthesis_morphing_permitted,
    synthesis_morphing,
)
from voicevox_engine.morphing import (
    synthesis_morphing_parameter as _synthesis_morphing_parameter,
)
from voicevox_engine.preset.Preset import Preset
from voicevox_engine.preset.PresetError import PresetError
from voicevox_engine.preset.PresetManager import PresetManager
from voicevox_engine.setting.Setting import CorsPolicyMode, Setting
from voicevox_engine.setting.SettingLoader import USER_SETTING_PATH, SettingHandler
from voicevox_engine.tts_pipeline.kana_converter import create_kana, parse_kana
from voicevox_engine.tts_pipeline.tts_engine import (
    TTSEngine,
    make_tts_engines_from_cores,
)
from voicevox_engine.user_dict.part_of_speech_data import MAX_PRIORITY, MIN_PRIORITY
from voicevox_engine.user_dict.user_dict import (
    apply_word,
    delete_word,
    import_user_dict,
    read_dict,
    rewrite_word,
    update_dict,
)
from voicevox_engine.utility.connect_base64_waves import (
    ConnectBase64WavesException,
    connect_base64_waves,
)
from voicevox_engine.utility.core_version_utility import get_latest_core_version
from voicevox_engine.utility.path_utility import delete_file, engine_root, get_save_dir
from voicevox_engine.utility.run_utility import decide_boolean_from_env


def b64encode_str(s):
    return base64.b64encode(s).decode("utf-8")


def set_output_log_utf8() -> None:
    """
    stdout/stderrのエンコーディングをUTF-8に切り替える関数
    """
    # コンソールがない環境だとNone https://docs.python.org/ja/3/library/sys.html#sys.__stdin__
    if sys.stdout is not None:
        if isinstance(sys.stdout, TextIOWrapper):
            sys.stdout.reconfigure(encoding="utf-8")
        else:
            # バッファを全て出力する
            sys.stdout.flush()
            try:
                sys.stdout = TextIOWrapper(
                    sys.stdout.buffer, encoding="utf-8", errors="backslashreplace"
                )
            except AttributeError:
                # stdout.bufferがない場合は無視
                pass
    if sys.stderr is not None:
        if isinstance(sys.stderr, TextIOWrapper):
            sys.stderr.reconfigure(encoding="utf-8")
        else:
            sys.stderr.flush()
            try:
                sys.stderr = TextIOWrapper(
                    sys.stderr.buffer, encoding="utf-8", errors="backslashreplace"
                )
            except AttributeError:
                # stderr.bufferがない場合は無視
                pass


def generate_app(
    tts_engines: dict[str, TTSEngine],
    cores: dict[str, CoreAdapter],
    latest_core_version: str,
    setting_loader: SettingHandler,
    preset_manager: PresetManager,
    cancellable_engine: CancellableEngine | None = None,
    root_dir: Optional[Path] = None,
    cors_policy_mode: CorsPolicyMode = CorsPolicyMode.localapps,
    allow_origin: Optional[list[str]] = None,
    disable_mutable_api: bool = False,
) -> FastAPI:
    if root_dir is None:
        root_dir = engine_root()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        update_dict()
        yield

    app = FastAPI(
        title="VOICEVOX Engine",
        description="VOICEVOXの音声合成エンジンです。",
        version=__version__,
        lifespan=lifespan,
    )

    # 未処理の例外が発生するとCORSMiddlewareが適用されない問題に対するワークアラウンド
    # ref: https://github.com/VOICEVOX/voicevox_engine/issues/91
    async def global_execution_handler(request: Request, exc: Exception) -> Response:
        return JSONResponse(
            status_code=500,
            content="Internal Server Error",
        )

    app.add_middleware(ServerErrorMiddleware, handler=global_execution_handler)

    # CORS用のヘッダを生成するミドルウェア
    localhost_regex = "^https?://(localhost|127\\.0\\.0\\.1)(:[0-9]+)?$"
    compiled_localhost_regex = re.compile(localhost_regex)
    allowed_origins = ["*"]
    if cors_policy_mode == "localapps":
        allowed_origins = ["app://."]
        if allow_origin is not None:
            allowed_origins += allow_origin
            if "*" in allow_origin:
                print(
                    'WARNING: Deprecated use of argument "*" in allow_origin. '
                    'Use option "--cors_policy_mod all" instead. See "--help" for more.',
                    file=sys.stderr,
                )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_origin_regex=localhost_regex,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 許可されていないOriginを遮断するミドルウェア
    @app.middleware("http")
    async def block_origin_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response | JSONResponse:
        isValidOrigin: bool = False
        if "Origin" not in request.headers:  # Originのない純粋なリクエストの場合
            isValidOrigin = True
        elif "*" in allowed_origins:  # すべてを許可する設定の場合
            isValidOrigin = True
        elif request.headers["Origin"] in allowed_origins:  # Originが許可されている場合
            isValidOrigin = True
        elif compiled_localhost_regex.fullmatch(
            request.headers["Origin"]
        ):  # localhostの場合
            isValidOrigin = True

        if isValidOrigin:
            return await call_next(request)
        else:
            return JSONResponse(
                status_code=403, content={"detail": "Origin not allowed"}
            )

    # 許可されていないAPIを無効化する
    def check_disabled_mutable_api() -> None:
        if disable_mutable_api:
            raise HTTPException(
                status_code=403,
                detail="エンジンの静的なデータを変更するAPIは無効化されています",
            )

    engine_manifest_data = EngineManifestLoader(
        engine_root() / "engine_manifest.json", engine_root()
    ).load_manifest()
    library_manager = LibraryManager(
        get_save_dir() / "installed_libraries",
        engine_manifest_data.supported_vvlib_manifest_version,
        engine_manifest_data.brand_name,
        engine_manifest_data.name,
        engine_manifest_data.uuid,
    )

    metas_store = MetasStore(root_dir / "speaker_info")

    setting_ui_template = Jinja2Templates(
        directory=engine_root() / "ui_template",
        variable_start_string="<JINJA_PRE>",
        variable_end_string="<JINJA_POST>",
    )

    # キャッシュを有効化
    # モジュール側でlru_cacheを指定するとキャッシュを制御しにくいため、HTTPサーバ側で指定する
    # TODO: キャッシュを管理するモジュール側API・HTTP側APIを用意する
    synthesis_morphing_parameter = lru_cache(maxsize=4)(_synthesis_morphing_parameter)

    # @app.on_event("startup")
    # async def start_catch_disconnection():
    #     if cancellable_engine is not None:
    #         loop = asyncio.get_event_loop()
    #         _ = loop.create_task(cancellable_engine.catch_disconnection())

    def get_engine(core_version: Optional[str]) -> TTSEngine:
        if core_version is None:
            return tts_engines[latest_core_version]
        if core_version in tts_engines:
            return tts_engines[core_version]
        raise HTTPException(status_code=422, detail="不明なバージョンです")

    def get_core(core_version: Optional[str]) -> CoreAdapter:
        """指定したバージョンのコアを取得する"""
        if core_version is None:
            return cores[latest_core_version]
        if core_version in cores:
            return cores[core_version]
        raise HTTPException(status_code=422, detail="不明なバージョンです")

    @app.post(
        "/audio_query",
        response_model=AudioQuery,
        tags=["クエリ作成"],
        summary="音声合成用のクエリを作成する",
    )
    def audio_query(
        text: str,
        style_id: StyleId = Query(alias="speaker"),  # noqa: B008
        core_version: str | None = None,
    ) -> AudioQuery:
        """
        音声合成用のクエリの初期値を得ます。ここで得られたクエリはそのまま音声合成に利用できます。各値の意味は`Schemas`を参照してください。
        """
        engine = get_engine(core_version)
        core = get_core(core_version)
        accent_phrases = engine.create_accent_phrases(text, style_id)
        return AudioQuery(
            accent_phrases=accent_phrases,
            speedScale=1,
            pitchScale=0,
            intonationScale=1,
            volumeScale=1,
            prePhonemeLength=0.1,
            postPhonemeLength=0.1,
            outputSamplingRate=core.default_sampling_rate,
            outputStereo=False,
            kana=create_kana(accent_phrases),
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
        core_version: str | None = None,
    ) -> AudioQuery:
        """
        音声合成用のクエリの初期値を得ます。ここで得られたクエリはそのまま音声合成に利用できます。各値の意味は`Schemas`を参照してください。
        """
        engine = get_engine(core_version)
        core = get_core(core_version)
        try:
            presets = preset_manager.load_presets()
        except PresetError as err:
            raise HTTPException(status_code=422, detail=str(err))
        for preset in presets:
            if preset.id == preset_id:
                selected_preset = preset
                break
        else:
            raise HTTPException(
                status_code=422, detail="該当するプリセットIDが見つかりません"
            )

        accent_phrases = engine.create_accent_phrases(text, selected_preset.style_id)
        return AudioQuery(
            accent_phrases=accent_phrases,
            speedScale=selected_preset.speedScale,
            pitchScale=selected_preset.pitchScale,
            intonationScale=selected_preset.intonationScale,
            volumeScale=selected_preset.volumeScale,
            prePhonemeLength=selected_preset.prePhonemeLength,
            postPhonemeLength=selected_preset.postPhonemeLength,
            outputSamplingRate=core.default_sampling_rate,
            outputStereo=False,
            kana=create_kana(accent_phrases),
        )

    @app.post(
        "/accent_phrases",
        response_model=list[AccentPhrase],
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
        style_id: StyleId = Query(alias="speaker"),  # noqa: B008
        is_kana: bool = False,
        core_version: str | None = None,
    ) -> list[AccentPhrase]:
        """
        テキストからアクセント句を得ます。
        is_kanaが`true`のとき、テキストは次のAquesTalk 風記法で解釈されます。デフォルトは`false`です。
        * 全てのカナはカタカナで記述される
        * アクセント句は`/`または`、`で区切る。`、`で区切った場合に限り無音区間が挿入される。
        * カナの手前に`_`を入れるとそのカナは無声化される
        * アクセント位置を`'`で指定する。全てのアクセント句にはアクセント位置を1つ指定する必要がある。
        * アクセント句末に`？`(全角)を入れることにより疑問文の発音ができる。
        """
        engine = get_engine(core_version)
        if is_kana:
            try:
                return engine.create_accent_phrases_from_kana(text, style_id)
            except ParseKanaError as err:
                raise HTTPException(
                    status_code=400, detail=ParseKanaBadRequest(err).dict()
                )
        else:
            return engine.create_accent_phrases(text, style_id)

    @app.post(
        "/mora_data",
        response_model=list[AccentPhrase],
        tags=["クエリ編集"],
        summary="アクセント句から音高・音素長を得る",
    )
    def mora_data(
        accent_phrases: list[AccentPhrase],
        style_id: StyleId = Query(alias="speaker"),  # noqa: B008
        core_version: str | None = None,
    ) -> list[AccentPhrase]:
        engine = get_engine(core_version)
        return engine.update_length_and_pitch(accent_phrases, style_id)

    @app.post(
        "/mora_length",
        response_model=list[AccentPhrase],
        tags=["クエリ編集"],
        summary="アクセント句から音素長を得る",
    )
    def mora_length(
        accent_phrases: list[AccentPhrase],
        style_id: StyleId = Query(alias="speaker"),  # noqa: B008
        core_version: str | None = None,
    ) -> list[AccentPhrase]:
        engine = get_engine(core_version)
        return engine.update_length(accent_phrases, style_id)

    @app.post(
        "/mora_pitch",
        response_model=list[AccentPhrase],
        tags=["クエリ編集"],
        summary="アクセント句から音高を得る",
    )
    def mora_pitch(
        accent_phrases: list[AccentPhrase],
        style_id: StyleId = Query(alias="speaker"),  # noqa: B008
        core_version: str | None = None,
    ) -> list[AccentPhrase]:
        engine = get_engine(core_version)
        return engine.update_pitch(accent_phrases, style_id)

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
    def synthesis(
        query: AudioQuery,
        style_id: StyleId = Query(alias="speaker"),  # noqa: B008
        enable_interrogative_upspeak: bool = Query(  # noqa: B008
            default=True,
            description="疑問系のテキストが与えられたら語尾を自動調整する",
        ),
        core_version: str | None = None,
    ) -> FileResponse:
        engine = get_engine(core_version)
        wave = engine.synthesize_wave(
            query, style_id, enable_interrogative_upspeak=enable_interrogative_upspeak
        )

        with NamedTemporaryFile(delete=False) as f:
            soundfile.write(
                file=f, data=wave, samplerate=query.outputSamplingRate, format="WAV"
            )

        return FileResponse(
            f.name,
            media_type="audio/wav",
            background=BackgroundTask(delete_file, f.name),
        )

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
        query: AudioQuery,
        request: Request,
        style_id: StyleId = Query(alias="speaker"),  # noqa: B008
        core_version: str | None = None,
    ) -> FileResponse:
        if cancellable_engine is None:
            raise HTTPException(
                status_code=404,
                detail="実験的機能はデフォルトで無効になっています。使用するには引数を指定してください。",
            )
        f_name = cancellable_engine._synthesis_impl(
            query, style_id, request, core_version=core_version
        )
        if f_name == "":
            raise HTTPException(status_code=422, detail="不明なバージョンです")

        return FileResponse(
            f_name,
            media_type="audio/wav",
            background=BackgroundTask(delete_file, f_name),
        )

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
    def multi_synthesis(
        queries: list[AudioQuery],
        style_id: StyleId = Query(alias="speaker"),  # noqa: B008
        core_version: str | None = None,
    ) -> FileResponse:
        engine = get_engine(core_version)
        sampling_rate = queries[0].outputSamplingRate

        with NamedTemporaryFile(delete=False) as f:
            with zipfile.ZipFile(f, mode="a") as zip_file:
                for i in range(len(queries)):
                    if queries[i].outputSamplingRate != sampling_rate:
                        raise HTTPException(
                            status_code=422,
                            detail="サンプリングレートが異なるクエリがあります",
                        )

                    with TemporaryFile() as wav_file:
                        wave = engine.synthesize_wave(queries[i], style_id)
                        soundfile.write(
                            file=wav_file,
                            data=wave,
                            samplerate=sampling_rate,
                            format="WAV",
                        )
                        wav_file.seek(0)
                        zip_file.writestr(f"{str(i + 1).zfill(3)}.wav", wav_file.read())

        return FileResponse(
            f.name,
            media_type="application/zip",
            background=BackgroundTask(delete_file, f.name),
        )

    @app.post(
        "/morphable_targets",
        response_model=list[dict[str, MorphableTargetInfo]],
        tags=["音声合成"],
        summary="指定したスタイルに対してエンジン内の話者がモーフィングが可能か判定する",
    )
    def morphable_targets(
        base_style_ids: list[StyleId], core_version: str | None = None
    ) -> list[dict[str, MorphableTargetInfo]]:
        """
        指定されたベーススタイルに対してエンジン内の各話者がモーフィング機能を利用可能か返します。
        モーフィングの許可/禁止は`/speakers`の`speaker.supported_features.synthesis_morphing`に記載されています。
        プロパティが存在しない場合は、モーフィングが許可されているとみなします。
        返り値のスタイルIDはstring型なので注意。
        """
        core = get_core(core_version)

        try:
            speakers = metas_store.load_combined_metas(core=core)
            morphable_targets = get_morphable_targets(
                speakers=speakers, base_style_ids=base_style_ids
            )
            # jsonはint型のキーを持てないので、string型に変換する
            return [
                {str(k): v for k, v in morphable_target.items()}
                for morphable_target in morphable_targets
            ]
        except StyleIdNotFoundError as e:
            raise HTTPException(
                status_code=404,
                detail=f"該当するスタイル(style_id={e.style_id})が見つかりません",
            )

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
        summary="2種類のスタイルでモーフィングした音声を合成する",
    )
    def _synthesis_morphing(
        query: AudioQuery,
        base_style_id: StyleId = Query(alias="base_speaker"),  # noqa: B008
        target_style_id: StyleId = Query(alias="target_speaker"),  # noqa: B008
        morph_rate: float = Query(..., ge=0.0, le=1.0),  # noqa: B008
        core_version: str | None = None,
    ) -> FileResponse:
        """
        指定された2種類のスタイルで音声を合成、指定した割合でモーフィングした音声を得ます。
        モーフィングの割合は`morph_rate`で指定でき、0.0でベースのスタイル、1.0でターゲットのスタイルに近づきます。
        """
        engine = get_engine(core_version)
        core = get_core(core_version)

        try:
            speakers = metas_store.load_combined_metas(core=core)
            speaker_lookup = construct_lookup(speakers=speakers)
            is_permitted = is_synthesis_morphing_permitted(
                speaker_lookup, base_style_id, target_style_id
            )
            if not is_permitted:
                raise HTTPException(
                    status_code=400,
                    detail="指定されたスタイルペアでのモーフィングはできません",
                )
        except StyleIdNotFoundError as e:
            raise HTTPException(
                status_code=404,
                detail=f"該当するスタイル(style_id={e.style_id})が見つかりません",
            )

        # 生成したパラメータはキャッシュされる
        morph_param = synthesis_morphing_parameter(
            engine=engine,
            core=core,
            query=query,
            base_style_id=base_style_id,
            target_style_id=target_style_id,
        )

        morph_wave = synthesis_morphing(
            morph_param=morph_param,
            morph_rate=morph_rate,
            output_fs=query.outputSamplingRate,
            output_stereo=query.outputStereo,
        )

        with NamedTemporaryFile(delete=False) as f:
            soundfile.write(
                file=f,
                data=morph_wave,
                samplerate=query.outputSamplingRate,
                format="WAV",
            )

        return FileResponse(
            f.name,
            media_type="audio/wav",
            background=BackgroundTask(delete_file, f.name),
        )

    @app.post(
        "/sing_frame_audio_query",
        response_model=FrameAudioQuery,
        tags=["クエリ作成"],
        summary="歌唱音声合成用のクエリを作成する",
    )
    def sing_frame_audio_query(
        score: Score,
        style_id: StyleId = Query(alias="speaker"),  # noqa: B008
        core_version: str | None = None,
    ) -> FrameAudioQuery:
        """
        歌唱音声合成用のクエリの初期値を得ます。ここで得られたクエリはそのまま歌唱音声合成に利用できます。各値の意味は`Schemas`を参照してください。
        """
        engine = get_engine(core_version)
        core = get_core(core_version)
        phonemes, f0, volume = engine.create_sing_phoneme_and_f0_and_volume(
            score, style_id
        )

        return FrameAudioQuery(
            f0=f0,
            volume=volume,
            phonemes=phonemes,
            volumeScale=1,
            outputSamplingRate=core.default_sampling_rate,
            outputStereo=False,
        )

    @app.post(
        "/frame_synthesis",
        response_class=FileResponse,
        responses={
            200: {
                "content": {
                    "audio/wav": {"schema": {"type": "string", "format": "binary"}}
                },
            }
        },
        tags=["音声合成"],
    )
    def frame_synthesis(
        query: FrameAudioQuery,
        style_id: StyleId = Query(alias="speaker"),  # noqa: B008
        core_version: str | None = None,
    ) -> FileResponse:
        """
        歌唱音声合成を行います。
        """
        engine = get_engine(core_version)
        wave = engine.frame_synthsize_wave(query, style_id)

        with NamedTemporaryFile(delete=False) as f:
            soundfile.write(
                file=f, data=wave, samplerate=query.outputSamplingRate, format="WAV"
            )

        return FileResponse(
            f.name,
            media_type="audio/wav",
            background=BackgroundTask(delete_file, f.name),
        )

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
    def connect_waves(waves: list[str]) -> FileResponse:
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

        return FileResponse(
            f.name,
            media_type="audio/wav",
            background=BackgroundTask(delete_file, f.name),
        )

    @app.get(
        "/presets",
        response_model=list[Preset],
        response_description="プリセットのリスト",
        tags=["その他"],
    )
    def get_presets() -> list[Preset]:
        """
        エンジンが保持しているプリセットの設定を返します
        """
        try:
            presets = preset_manager.load_presets()
        except PresetError as err:
            raise HTTPException(status_code=422, detail=str(err))
        return presets

    @app.post(
        "/add_preset",
        response_model=int,
        response_description="追加したプリセットのプリセットID",
        tags=["その他"],
        dependencies=[Depends(check_disabled_mutable_api)],
    )
    def add_preset(
        preset: Annotated[
            Preset,
            Body(
                description="新しいプリセット。プリセットIDが既存のものと重複している場合は、新規のプリセットIDが採番されます。"
            ),
        ]
    ) -> int:
        """
        新しいプリセットを追加します
        """
        try:
            id = preset_manager.add_preset(preset)
        except PresetError as err:
            raise HTTPException(status_code=422, detail=str(err))
        return id

    @app.post(
        "/update_preset",
        response_model=int,
        response_description="更新したプリセットのプリセットID",
        tags=["その他"],
        dependencies=[Depends(check_disabled_mutable_api)],
    )
    def update_preset(
        preset: Annotated[
            Preset,
            Body(
                description="更新するプリセット。プリセットIDが更新対象と一致している必要があります。"
            ),
        ]
    ) -> int:
        """
        既存のプリセットを更新します
        """
        try:
            id = preset_manager.update_preset(preset)
        except PresetError as err:
            raise HTTPException(status_code=422, detail=str(err))
        return id

    @app.post(
        "/delete_preset",
        status_code=204,
        tags=["その他"],
        dependencies=[Depends(check_disabled_mutable_api)],
    )
    def delete_preset(
        id: Annotated[int, Query(description="削除するプリセットのプリセットID")]
    ) -> Response:
        """
        既存のプリセットを削除します
        """
        try:
            preset_manager.delete_preset(id)
        except PresetError as err:
            raise HTTPException(status_code=422, detail=str(err))
        return Response(status_code=204)

    @app.get("/version", tags=["その他"])
    def version() -> str:
        return __version__

    @app.get("/core_versions", response_model=list[str], tags=["その他"])
    def core_versions() -> Response:
        return Response(
            content=json.dumps(list(cores.keys())),
            media_type="application/json",
        )

    @app.get("/speakers", response_model=list[Speaker], tags=["その他"])
    def speakers(
        core_version: str | None = None,
    ) -> list[Speaker]:
        speakers = metas_store.load_combined_metas(get_core(core_version))
        return filter_speakers_and_styles(speakers, "speaker")

    @app.get("/speaker_info", response_model=SpeakerInfo, tags=["その他"])
    def speaker_info(
        speaker_uuid: str,
        core_version: str | None = None,
    ) -> SpeakerInfo:
        """
        指定されたspeaker_uuidに関する情報をjson形式で返します。
        画像や音声はbase64エンコードされたものが返されます。
        """
        return _speaker_info(
            speaker_uuid=speaker_uuid,
            speaker_or_singer="speaker",
            core_version=core_version,
        )

    # FIXME: この関数をどこかに切り出す
    def _speaker_info(
        speaker_uuid: str,
        speaker_or_singer: Literal["speaker", "singer"],
        core_version: str | None,
    ) -> SpeakerInfo:
        # エンジンに含まれる話者メタ情報は、次のディレクトリ構造に従わなければならない：
        # {root_dir}/
        #   speaker_info/
        #       {speaker_uuid_0}/
        #           policy.md
        #           portrait.png
        #           icons/
        #               {id_0}.png
        #               {id_1}.png
        #               ...
        #           portraits/
        #               {id_0}.png
        #               {id_1}.png
        #               ...
        #           voice_samples/
        #               {id_0}_001.wav
        #               {id_0}_002.wav
        #               {id_0}_003.wav
        #               {id_1}_001.wav
        #               ...
        #       {speaker_uuid_1}/
        #           ...

        # 該当話者の検索
        speakers = parse_obj_as(
            list[Speaker], json.loads(get_core(core_version).speakers)
        )
        speakers = filter_speakers_and_styles(speakers, speaker_or_singer)
        for i in range(len(speakers)):
            if speakers[i].speaker_uuid == speaker_uuid:
                speaker = speakers[i]
                break
        else:
            raise HTTPException(status_code=404, detail="該当する話者が見つかりません")

        try:
            speaker_path = root_dir / "speaker_info" / speaker_uuid
            # 話者情報の取得
            # speaker policy
            policy_path = speaker_path / "policy.md"
            policy = policy_path.read_text("utf-8")
            # speaker portrait
            portrait_path = speaker_path / "portrait.png"
            portrait = b64encode_str(portrait_path.read_bytes())
            # スタイル情報の取得
            style_infos = []
            for style in speaker.styles:
                id = style.id
                # style icon
                style_icon_path = speaker_path / "icons" / f"{id}.png"
                icon = b64encode_str(style_icon_path.read_bytes())
                # style portrait
                style_portrait_path = speaker_path / "portraits" / f"{id}.png"
                style_portrait = None
                if style_portrait_path.exists():
                    style_portrait = b64encode_str(style_portrait_path.read_bytes())
                # voice samples
                voice_samples = [
                    b64encode_str(
                        (
                            speaker_path
                            / "voice_samples/{}_{}.wav".format(id, str(j + 1).zfill(3))
                        ).read_bytes()
                    )
                    for j in range(3)
                ]
                style_infos.append(
                    {
                        "id": id,
                        "icon": icon,
                        "portrait": style_portrait,
                        "voice_samples": voice_samples,
                    }
                )
        except FileNotFoundError:
            import traceback

            traceback.print_exc()
            raise HTTPException(
                status_code=500, detail="追加情報が見つかりませんでした"
            )

        ret_data = SpeakerInfo(
            policy=policy,
            portrait=portrait,
            style_infos=style_infos,
        )
        return ret_data

    @app.get("/singers", response_model=list[Speaker], tags=["その他"])
    def singers(
        core_version: str | None = None,
    ) -> list[Speaker]:
        singers = metas_store.load_combined_metas(get_core(core_version))
        return filter_speakers_and_styles(singers, "singer")

    @app.get("/singer_info", response_model=SpeakerInfo, tags=["その他"])
    def singer_info(
        speaker_uuid: str,
        core_version: str | None = None,
    ) -> SpeakerInfo:
        """
        指定されたspeaker_uuidに関する情報をjson形式で返します。
        画像や音声はbase64エンコードされたものが返されます。
        """
        return _speaker_info(
            speaker_uuid=speaker_uuid,
            speaker_or_singer="singer",
            core_version=core_version,
        )

    if engine_manifest_data.supported_features.manage_library:

        @app.get(
            "/downloadable_libraries",
            response_model=list[DownloadableLibraryInfo],
            response_description="ダウンロード可能な音声ライブラリの情報リスト",
            tags=["音声ライブラリ管理"],
        )
        def downloadable_libraries() -> list[DownloadableLibraryInfo]:
            """
            ダウンロード可能な音声ライブラリの情報を返します。
            """
            if not engine_manifest_data.supported_features.manage_library:
                raise HTTPException(
                    status_code=404, detail="この機能は実装されていません"
                )
            return library_manager.downloadable_libraries()

        @app.get(
            "/installed_libraries",
            response_model=dict[str, InstalledLibraryInfo],
            response_description="インストールした音声ライブラリの情報",
            tags=["音声ライブラリ管理"],
        )
        def installed_libraries() -> dict[str, InstalledLibraryInfo]:
            """
            インストールした音声ライブラリの情報を返します。
            """
            if not engine_manifest_data.supported_features.manage_library:
                raise HTTPException(
                    status_code=404, detail="この機能は実装されていません"
                )
            return library_manager.installed_libraries()

        @app.post(
            "/install_library/{library_uuid}",
            status_code=204,
            tags=["音声ライブラリ管理"],
            dependencies=[Depends(check_disabled_mutable_api)],
        )
        async def install_library(
            library_uuid: Annotated[str, FAPath(description="音声ライブラリのID")],
            request: Request,
        ) -> Response:
            """
            音声ライブラリをインストールします。
            音声ライブラリのZIPファイルをリクエストボディとして送信してください。
            """
            if not engine_manifest_data.supported_features.manage_library:
                raise HTTPException(
                    status_code=404, detail="この機能は実装されていません"
                )
            archive = BytesIO(await request.body())
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, library_manager.install_library, library_uuid, archive
            )
            return Response(status_code=204)

        @app.post(
            "/uninstall_library/{library_uuid}",
            status_code=204,
            tags=["音声ライブラリ管理"],
            dependencies=[Depends(check_disabled_mutable_api)],
        )
        def uninstall_library(
            library_uuid: Annotated[str, FAPath(description="音声ライブラリのID")]
        ) -> Response:
            """
            音声ライブラリをアンインストールします。
            """
            if not engine_manifest_data.supported_features.manage_library:
                raise HTTPException(
                    status_code=404, detail="この機能は実装されていません"
                )
            library_manager.uninstall_library(library_uuid)
            return Response(status_code=204)

    @app.post("/initialize_speaker", status_code=204, tags=["その他"])
    def initialize_speaker(
        style_id: StyleId = Query(alias="speaker"),  # noqa: B008
        skip_reinit: bool = Query(  # noqa: B008
            default=False,
            description="既に初期化済みのスタイルの再初期化をスキップするかどうか",
        ),
        core_version: str | None = None,
    ) -> Response:
        """
        指定されたスタイルを初期化します。
        実行しなくても他のAPIは使用できますが、初回実行時に時間がかかることがあります。
        """
        core = get_core(core_version)
        core.initialize_style_id_synthesis(style_id, skip_reinit=skip_reinit)
        return Response(status_code=204)

    @app.get("/is_initialized_speaker", response_model=bool, tags=["その他"])
    def is_initialized_speaker(
        style_id: StyleId = Query(alias="speaker"),  # noqa: B008
        core_version: str | None = None,
    ) -> bool:
        """
        指定されたスタイルが初期化されているかどうかを返します。
        """
        core = get_core(core_version)
        return core.is_initialized_style_id_synthesis(style_id)

    @app.get(
        "/user_dict",
        response_model=dict[str, UserDictWord],
        response_description="単語のUUIDとその詳細",
        tags=["ユーザー辞書"],
    )
    def get_user_dict_words() -> dict[str, UserDictWord]:
        """
        ユーザー辞書に登録されている単語の一覧を返します。
        単語の表層形(surface)は正規化済みの物を返します。
        """
        try:
            return read_dict()
        except Exception:
            traceback.print_exc()
            raise HTTPException(
                status_code=422, detail="辞書の読み込みに失敗しました。"
            )

    @app.post(
        "/user_dict_word",
        response_model=str,
        tags=["ユーザー辞書"],
        dependencies=[Depends(check_disabled_mutable_api)],
    )
    def add_user_dict_word(
        surface: Annotated[str, Query(description="言葉の表層形")],
        pronunciation: Annotated[str, Query(description="言葉の発音（カタカナ）")],
        accent_type: Annotated[
            int, Query(description="アクセント型（音が下がる場所を指す）")
        ],
        word_type: Annotated[
            WordTypes | None,
            Query(
                description="PROPER_NOUN（固有名詞）、COMMON_NOUN（普通名詞）、VERB（動詞）、ADJECTIVE（形容詞）、SUFFIX（語尾）のいずれか"
            ),
        ] = None,
        priority: Annotated[
            int | None,
            Query(
                ge=MIN_PRIORITY,
                le=MAX_PRIORITY,
                description="単語の優先度（0から10までの整数）。数字が大きいほど優先度が高くなる。1から9までの値を指定することを推奨",
            ),
        ] = None,
    ) -> Response:
        """
        ユーザー辞書に言葉を追加します。
        """
        try:
            word_uuid = apply_word(
                surface=surface,
                pronunciation=pronunciation,
                accent_type=accent_type,
                word_type=word_type,
                priority=priority,
            )
            return Response(content=word_uuid)
        except ValidationError as e:
            raise HTTPException(
                status_code=422, detail="パラメータに誤りがあります。\n" + str(e)
            )
        except Exception:
            traceback.print_exc()
            raise HTTPException(
                status_code=422, detail="ユーザー辞書への追加に失敗しました。"
            )

    @app.put(
        "/user_dict_word/{word_uuid}",
        status_code=204,
        tags=["ユーザー辞書"],
        dependencies=[Depends(check_disabled_mutable_api)],
    )
    def rewrite_user_dict_word(
        surface: Annotated[str, Query(description="言葉の表層形")],
        pronunciation: Annotated[str, Query(description="言葉の発音（カタカナ）")],
        accent_type: Annotated[
            int, Query(description="アクセント型（音が下がる場所を指す）")
        ],
        word_uuid: Annotated[str, FAPath(description="更新する言葉のUUID")],
        word_type: Annotated[
            WordTypes | None,
            Query(
                description="PROPER_NOUN（固有名詞）、COMMON_NOUN（普通名詞）、VERB（動詞）、ADJECTIVE（形容詞）、SUFFIX（語尾）のいずれか"
            ),
        ] = None,
        priority: Annotated[
            int | None,
            Query(
                ge=MIN_PRIORITY,
                le=MAX_PRIORITY,
                description="単語の優先度（0から10までの整数）。数字が大きいほど優先度が高くなる。1から9までの値を指定することを推奨。",
            ),
        ] = None,
    ) -> Response:
        """
        ユーザー辞書に登録されている言葉を更新します。
        """
        try:
            rewrite_word(
                surface=surface,
                pronunciation=pronunciation,
                accent_type=accent_type,
                word_uuid=word_uuid,
                word_type=word_type,
                priority=priority,
            )
            return Response(status_code=204)
        except HTTPException:
            raise
        except ValidationError as e:
            raise HTTPException(
                status_code=422, detail="パラメータに誤りがあります。\n" + str(e)
            )
        except Exception:
            traceback.print_exc()
            raise HTTPException(
                status_code=422, detail="ユーザー辞書の更新に失敗しました。"
            )

    @app.delete(
        "/user_dict_word/{word_uuid}",
        status_code=204,
        tags=["ユーザー辞書"],
        dependencies=[Depends(check_disabled_mutable_api)],
    )
    def delete_user_dict_word(
        word_uuid: Annotated[str, FAPath(description="削除する言葉のUUID")]
    ) -> Response:
        """
        ユーザー辞書に登録されている言葉を削除します。
        """
        try:
            delete_word(word_uuid=word_uuid)
            return Response(status_code=204)
        except HTTPException:
            raise
        except Exception:
            traceback.print_exc()
            raise HTTPException(
                status_code=422, detail="ユーザー辞書の更新に失敗しました。"
            )

    @app.post(
        "/import_user_dict",
        status_code=204,
        tags=["ユーザー辞書"],
        dependencies=[Depends(check_disabled_mutable_api)],
    )
    def import_user_dict_words(
        import_dict_data: Annotated[
            dict[str, UserDictWord],
            Body(description="インポートするユーザー辞書のデータ"),
        ],
        override: Annotated[
            bool, Query(description="重複したエントリがあった場合、上書きするかどうか")
        ],
    ) -> Response:
        """
        他のユーザー辞書をインポートします。
        """
        try:
            import_user_dict(dict_data=import_dict_data, override=override)
            return Response(status_code=204)
        except Exception:
            traceback.print_exc()
            raise HTTPException(
                status_code=422, detail="ユーザー辞書のインポートに失敗しました。"
            )

    @app.get("/supported_devices", response_model=SupportedDevicesInfo, tags=["その他"])
    def supported_devices(
        core_version: str | None = None,
    ) -> Response:
        supported_devices = get_core(core_version).supported_devices
        if supported_devices is None:
            raise HTTPException(status_code=422, detail="非対応の機能です。")
        return Response(
            content=supported_devices,
            media_type="application/json",
        )

    @app.get("/engine_manifest", response_model=EngineManifest, tags=["その他"])
    def engine_manifest() -> EngineManifest:
        return engine_manifest_data

    @app.post(
        "/validate_kana",
        response_model=bool,
        tags=["その他"],
        summary="テキストがAquesTalk 風記法に従っているか判定する",
        responses={
            400: {
                "description": "テキストが不正です",
                "model": ParseKanaBadRequest,
            }
        },
    )
    def validate_kana(
        text: Annotated[str, Query(description="判定する対象の文字列")]
    ) -> bool:
        """
        テキストがAquesTalk 風記法に従っているかどうかを判定します。
        従っていない場合はエラーが返ります。
        """
        try:
            parse_kana(text)
            return True
        except ParseKanaError as err:
            raise HTTPException(
                status_code=400,
                detail=ParseKanaBadRequest(err).dict(),
            )

    @app.get("/setting", response_class=Response, tags=["設定"])
    def setting_get(request: Request) -> Response:
        """
        設定ページを返します。
        """
        settings = setting_loader.load()

        brand_name = engine_manifest_data.brand_name
        cors_policy_mode = settings.cors_policy_mode
        allow_origin = settings.allow_origin

        if allow_origin is None:
            allow_origin = ""

        return setting_ui_template.TemplateResponse(
            "ui.html",
            {
                "request": request,
                "brand_name": brand_name,
                "cors_policy_mode": cors_policy_mode.value,
                "allow_origin": allow_origin,
            },
        )

    @app.post(
        "/setting",
        response_class=Response,
        tags=["設定"],
        dependencies=[Depends(check_disabled_mutable_api)],
    )
    def setting_post(
        cors_policy_mode: CorsPolicyMode = Form(),  # noqa
        allow_origin: str | None = Form(default=None),  # noqa
    ) -> Response:
        """
        設定を更新します。
        """
        settings = Setting(
            cors_policy_mode=cors_policy_mode,
            allow_origin=allow_origin,
        )

        # 更新した設定へ上書き
        setting_loader.save(settings)

        return Response(status_code=204)

    # BaseLibraryInfo/VvlibManifestモデルはAPIとして表には出ないが、エディタ側で利用したいので、手動で追加する
    # ref: https://fastapi.tiangolo.com/advanced/extending-openapi/#modify-the-openapi-schema
    def custom_openapi() -> Any:
        if app.openapi_schema:
            return app.openapi_schema
        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
            tags=app.openapi_tags,
            servers=app.servers,
            terms_of_service=app.terms_of_service,
            contact=app.contact,
            license_info=app.license_info,
        )
        openapi_schema["components"]["schemas"][
            "VvlibManifest"
        ] = VvlibManifest.schema()
        # ref_templateを指定しない場合、definitionsを参照してしまうので、手動で指定する
        base_library_info = BaseLibraryInfo.schema(
            ref_template="#/components/schemas/{model}"
        )
        # definitionsは既存のモデルを重複して定義するため、不要なので削除
        del base_library_info["definitions"]
        openapi_schema["components"]["schemas"]["BaseLibraryInfo"] = base_library_info
        app.openapi_schema = openapi_schema
        return openapi_schema

    app.openapi = custom_openapi  # type: ignore[method-assign]

    return app


def main() -> None:
    multiprocessing.freeze_support()

    output_log_utf8 = decide_boolean_from_env("VV_OUTPUT_LOG_UTF8")
    if output_log_utf8:
        set_output_log_utf8()

    parser = argparse.ArgumentParser(description="VOICEVOX のエンジンです。")
    # Uvicorn でバインドするアドレスを "localhost" にすることで IPv4 (127.0.0.1) と IPv6 ([::1]) の両方でリッスンできます.
    # これは Uvicorn のドキュメントに記載されていない挙動です; 将来のアップデートにより動作しなくなる可能性があります.
    # ref: https://github.com/VOICEVOX/voicevox_engine/pull/647#issuecomment-1540204653
    parser.add_argument(
        "--host",
        type=str,
        default="localhost",
        help="接続を受け付けるホストアドレスです。",
    )
    parser.add_argument(
        "--port", type=int, default=50021, help="接続を受け付けるポート番号です。"
    )
    parser.add_argument(
        "--use_gpu", action="store_true", help="GPUを使って音声合成するようになります。"
    )
    parser.add_argument(
        "--voicevox_dir",
        type=Path,
        default=None,
        help="VOICEVOXのディレクトリパスです。",
    )
    parser.add_argument(
        "--voicelib_dir",
        type=Path,
        default=None,
        action="append",
        help="VOICEVOX COREのディレクトリパスです。",
    )
    parser.add_argument(
        "--runtime_dir",
        type=Path,
        default=None,
        action="append",
        help="VOICEVOX COREで使用するライブラリのディレクトリパスです。",
    )
    parser.add_argument(
        "--enable_mock",
        action="store_true",
        help="VOICEVOX COREを使わずモックで音声合成を行います。",
    )
    parser.add_argument(
        "--enable_cancellable_synthesis",
        action="store_true",
        help="音声合成を途中でキャンセルできるようになります。",
    )
    parser.add_argument(
        "--init_processes",
        type=int,
        default=2,
        help="cancellable_synthesis機能の初期化時に生成するプロセス数です。",
    )
    parser.add_argument(
        "--load_all_models",
        action="store_true",
        help="起動時に全ての音声合成モデルを読み込みます。",
    )

    # 引数へcpu_num_threadsの指定がなければ、環境変数をロールします。
    # 環境変数にもない場合は、Noneのままとします。
    # VV_CPU_NUM_THREADSが空文字列でなく数値でもない場合、エラー終了します。
    parser.add_argument(
        "--cpu_num_threads",
        type=int,
        default=os.getenv("VV_CPU_NUM_THREADS") or None,
        help=(
            "音声合成を行うスレッド数です。指定しない場合、代わりに環境変数 VV_CPU_NUM_THREADS の値が使われます。"
            "VV_CPU_NUM_THREADS が空文字列でなく数値でもない場合はエラー終了します。"
        ),
    )

    parser.add_argument(
        "--output_log_utf8",
        action="store_true",
        help=(
            "ログ出力をUTF-8でおこないます。指定しない場合、代わりに環境変数 VV_OUTPUT_LOG_UTF8 の値が使われます。"
            "VV_OUTPUT_LOG_UTF8 の値が1の場合はUTF-8で、0または空文字、値がない場合は環境によって自動的に決定されます。"
        ),
    )

    parser.add_argument(
        "--cors_policy_mode",
        type=CorsPolicyMode,
        choices=list(CorsPolicyMode),
        default=None,
        help=(
            "CORSの許可モード。allまたはlocalappsが指定できます。allはすべてを許可します。"
            "localappsはオリジン間リソース共有ポリシーを、app://.とlocalhost関連に限定します。"
            "その他のオリジンはallow_originオプションで追加できます。デフォルトはlocalapps。"
            "このオプションは--setting_fileで指定される設定ファイルよりも優先されます。"
        ),
    )

    parser.add_argument(
        "--allow_origin",
        nargs="*",
        help=(
            "許可するオリジンを指定します。スペースで区切ることで複数指定できます。"
            "このオプションは--setting_fileで指定される設定ファイルよりも優先されます。"
        ),
    )

    parser.add_argument(
        "--setting_file",
        type=Path,
        default=USER_SETTING_PATH,
        help="設定ファイルを指定できます。",
    )

    parser.add_argument(
        "--preset_file",
        type=Path,
        default=None,
        help=(
            "プリセットファイルを指定できます。"
            "指定がない場合、環境変数 VV_PRESET_FILE、--voicevox_dirのpresets.yaml、"
            "実行ファイルのディレクトリのpresets.yamlを順に探します。"
        ),
    )

    parser.add_argument(
        "--disable_mutable_api",
        action="store_true",
        help=(
            "辞書登録や設定変更など、エンジンの静的なデータを変更するAPIを無効化します。"
            "指定しない場合、代わりに環境変数 VV_DISABLE_MUTABLE_API の値が使われます。"
            "VV_DISABLE_MUTABLE_API の値が1の場合は無効化で、0または空文字、値がない場合は無視されます。"
        ),
    )

    args = parser.parse_args()

    if args.output_log_utf8:
        set_output_log_utf8()

    # Synthesis Engine
    use_gpu: bool = args.use_gpu
    voicevox_dir: Path | None = args.voicevox_dir
    voicelib_dirs: list[Path] | None = args.voicelib_dir
    runtime_dirs: list[Path] | None = args.runtime_dir
    enable_mock: bool = args.enable_mock
    cpu_num_threads: int | None = args.cpu_num_threads
    load_all_models: bool = args.load_all_models

    cores = initialize_cores(
        use_gpu=use_gpu,
        voicelib_dirs=voicelib_dirs,
        voicevox_dir=voicevox_dir,
        runtime_dirs=runtime_dirs,
        cpu_num_threads=cpu_num_threads,
        enable_mock=enable_mock,
        load_all_models=load_all_models,
    )
    tts_engines = make_tts_engines_from_cores(cores)
    assert len(tts_engines) != 0, "音声合成エンジンがありません。"
    latest_core_version = get_latest_core_version(versions=list(tts_engines.keys()))

    # Cancellable Engine
    enable_cancellable_synthesis: bool = args.enable_cancellable_synthesis
    init_processes: int = args.init_processes

    cancellable_engine: CancellableEngine | None = None
    if enable_cancellable_synthesis:
        cancellable_engine = CancellableEngine(
            init_processes=init_processes,
            use_gpu=use_gpu,
            voicelib_dirs=voicelib_dirs,
            voicevox_dir=voicevox_dir,
            runtime_dirs=runtime_dirs,
            cpu_num_threads=cpu_num_threads,
            enable_mock=enable_mock,
        )

    root_dir: Path | None = voicevox_dir
    if root_dir is None:
        root_dir = engine_root()

    setting_loader = SettingHandler(args.setting_file)

    settings = setting_loader.load()

    cors_policy_mode: CorsPolicyMode | None = args.cors_policy_mode
    if cors_policy_mode is None:
        cors_policy_mode = settings.cors_policy_mode

    allow_origin = None
    if args.allow_origin is not None:
        allow_origin = args.allow_origin
    elif settings.allow_origin is not None:
        allow_origin = settings.allow_origin.split(" ")

    # Preset Manager
    # preset_pathの優先順: 引数、環境変数、voicevox_dir、実行ファイルのディレクトリ
    # ファイルの存在に関わらず、優先順で最初に指定されたパスをプリセットファイルとして使用する
    preset_path: Path | None = args.preset_file
    if preset_path is None:
        # 引数 --preset_file の指定がない場合
        env_preset_path = os.getenv("VV_PRESET_FILE")
        if env_preset_path is not None and len(env_preset_path) != 0:
            # 環境変数 VV_PRESET_FILE の指定がある場合
            preset_path = Path(env_preset_path)
        else:
            # 環境変数 VV_PRESET_FILE の指定がない場合
            preset_path = root_dir / "presets.yaml"

    preset_manager = PresetManager(
        preset_path=preset_path,
    )

    disable_mutable_api: bool = args.disable_mutable_api | decide_boolean_from_env(
        "VV_DISABLE_MUTABLE_API"
    )

    uvicorn.run(
        generate_app(
            tts_engines,
            cores,
            latest_core_version,
            setting_loader,
            preset_manager=preset_manager,
            cancellable_engine=cancellable_engine,
            root_dir=root_dir,
            cors_policy_mode=cors_policy_mode,
            allow_origin=allow_origin,
            disable_mutable_api=disable_mutable_api,
        ),
        host=args.host,
        port=args.port,
    )


if __name__ == "__main__":
    main()
