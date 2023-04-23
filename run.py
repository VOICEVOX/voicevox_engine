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
from functools import lru_cache
from io import BytesIO, TextIOWrapper
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryFile
from typing import Dict, List, Optional

import soundfile
import uvicorn
from fastapi import FastAPI, Form, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError, conint
from starlette.background import BackgroundTask
from starlette.responses import FileResponse

from voicevox_engine import __version__
from voicevox_engine.cancellable_engine import CancellableEngine
from voicevox_engine.downloadable_library import LibraryManager
from voicevox_engine.engine_manifest import EngineManifestLoader
from voicevox_engine.engine_manifest.EngineManifest import EngineManifest
from voicevox_engine.kana_parser import create_kana, parse_kana
from voicevox_engine.metas.MetasStore import MetasStore, construct_lookup
from voicevox_engine.model import (
    AccentPhrase,
    AudioQuery,
    DownloadableLibrary,
    MorphableTargetInfo,
    ParseKanaBadRequest,
    ParseKanaError,
    Speaker,
    SpeakerInfo,
    SpeakerNotFoundError,
    SupportedDevicesInfo,
    UserDictWord,
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
from voicevox_engine.part_of_speech_data import MAX_PRIORITY, MIN_PRIORITY
from voicevox_engine.preset import Preset, PresetError, PresetManager
from voicevox_engine.setting import (
    USER_SETTING_PATH,
    CorsPolicyMode,
    Setting,
    SettingLoader,
)
from voicevox_engine.synthesis_engine import SynthesisEngineBase, make_synthesis_engines
from voicevox_engine.user_dict import (
    apply_word,
    delete_word,
    import_user_dict,
    read_dict,
    rewrite_word,
    update_dict,
)
from voicevox_engine.utility import (
    ConnectBase64WavesException,
    connect_base64_waves,
    delete_file,
    engine_root,
    get_latest_core_version,
    get_save_dir,
)


def b64encode_str(s):
    return base64.b64encode(s).decode("utf-8")


def set_output_log_utf8() -> None:
    """
    stdout/stderrのエンコーディングをUTF-8に切り替える関数
    """
    # コンソールがない環境だとNone https://docs.python.org/ja/3/library/sys.html#sys.__stdin__
    if sys.stdout is not None:
        # 必ずしもreconfigure()が実装されているとは限らない
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except AttributeError:
            # バッファを全て出力する
            sys.stdout.flush()
            sys.stdout = TextIOWrapper(
                sys.stdout.buffer, encoding="utf-8", errors="backslashreplace"
            )
    if sys.stderr is not None:
        try:
            sys.stderr.reconfigure(encoding="utf-8")
        except AttributeError:
            sys.stderr.flush()
            sys.stderr = TextIOWrapper(
                sys.stderr.buffer, encoding="utf-8", errors="backslashreplace"
            )


def generate_app(
    synthesis_engines: Dict[str, SynthesisEngineBase],
    latest_core_version: str,
    setting_loader: SettingLoader,
    root_dir: Optional[Path] = None,
    cors_policy_mode: CorsPolicyMode = CorsPolicyMode.localapps,
    allow_origin: Optional[List[str]] = None,
) -> FastAPI:
    if root_dir is None:
        root_dir = engine_root()

    default_sampling_rate = synthesis_engines[latest_core_version].default_sampling_rate

    app = FastAPI(
        title="VOICEVOX Engine",
        description="VOICEVOXの音声合成エンジンです。",
        version=__version__,
    )

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
    async def block_origin_middleware(request: Request, call_next):
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

    preset_manager = PresetManager(
        preset_path=root_dir / "presets.yaml",
    )
    engine_manifest_loader = EngineManifestLoader(
        root_dir / "engine_manifest.json", root_dir
    )
    library_manager = LibraryManager(get_save_dir() / "installed_libraries")

    metas_store = MetasStore(root_dir / "speaker_info")

    setting_ui_template = Jinja2Templates(directory=engine_root() / "ui_template")

    # キャッシュを有効化
    # モジュール側でlru_cacheを指定するとキャッシュを制御しにくいため、HTTPサーバ側で指定する
    # TODO: キャッシュを管理するモジュール側API・HTTP側APIを用意する
    synthesis_morphing_parameter = lru_cache(maxsize=4)(_synthesis_morphing_parameter)

    # @app.on_event("startup")
    # async def start_catch_disconnection():
    #     if args.enable_cancellable_synthesis:
    #         loop = asyncio.get_event_loop()
    #         _ = loop.create_task(cancellable_engine.catch_disconnection())

    @app.on_event("startup")
    def apply_user_dict():
        update_dict()

    def get_engine(core_version: Optional[str]) -> SynthesisEngineBase:
        if core_version is None:
            return synthesis_engines[latest_core_version]
        if core_version in synthesis_engines:
            return synthesis_engines[core_version]
        raise HTTPException(status_code=422, detail="不明なバージョンです")

    @app.post(
        "/audio_query",
        response_model=AudioQuery,
        tags=["クエリ作成"],
        summary="音声合成用のクエリを作成する",
    )
    def audio_query(text: str, speaker: int, core_version: Optional[str] = None):
        """
        クエリの初期値を得ます。ここで得られたクエリはそのまま音声合成に利用できます。各値の意味は`Schemas`を参照してください。
        """
        engine = get_engine(core_version)
        accent_phrases = engine.create_accent_phrases(text, speaker_id=speaker)
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
        "/audio_query_from_preset",
        response_model=AudioQuery,
        tags=["クエリ作成"],
        summary="音声合成用のクエリをプリセットを用いて作成する",
    )
    def audio_query_from_preset(
        text: str, preset_id: int, core_version: Optional[str] = None
    ):
        """
        クエリの初期値を得ます。ここで得られたクエリはそのまま音声合成に利用できます。各値の意味は`Schemas`を参照してください。
        """
        engine = get_engine(core_version)
        try:
            presets = preset_manager.load_presets()
        except PresetError as err:
            raise HTTPException(status_code=422, detail=str(err))
        for preset in presets:
            if preset.id == preset_id:
                selected_preset = preset
                break
        else:
            raise HTTPException(status_code=422, detail="該当するプリセットIDが見つかりません")

        accent_phrases = engine.create_accent_phrases(
            text, speaker_id=selected_preset.style_id
        )
        return AudioQuery(
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
        core_version: Optional[str] = None,
    ):
        """
        テキストからアクセント句を得ます。
        is_kanaが`true`のとき、テキストは次のようなAquesTalkライクな記法に従う読み仮名として処理されます。デフォルトは`false`です。
        * 全てのカナはカタカナで記述される
        * アクセント句は`/`または`、`で区切る。`、`で区切った場合に限り無音区間が挿入される。
        * カナの手前に`_`を入れるとそのカナは無声化される
        * アクセント位置を`'`で指定する。全てのアクセント句にはアクセント位置を1つ指定する必要がある。
        * アクセント句末に`？`(全角)を入れることにより疑問文の発音ができる。
        """
        engine = get_engine(core_version)
        if is_kana:
            try:
                accent_phrases = parse_kana(text)
            except ParseKanaError as err:
                raise HTTPException(
                    status_code=400,
                    detail=ParseKanaBadRequest(err).dict(),
                )
            accent_phrases = engine.replace_mora_data(
                accent_phrases=accent_phrases, speaker_id=speaker
            )

            return accent_phrases
        else:
            return engine.create_accent_phrases(text, speaker_id=speaker)

    @app.post(
        "/mora_data",
        response_model=List[AccentPhrase],
        tags=["クエリ編集"],
        summary="アクセント句から音高・音素長を得る",
    )
    def mora_data(
        accent_phrases: List[AccentPhrase],
        speaker: int,
        core_version: Optional[str] = None,
    ):
        engine = get_engine(core_version)
        return engine.replace_mora_data(accent_phrases, speaker_id=speaker)

    @app.post(
        "/mora_length",
        response_model=List[AccentPhrase],
        tags=["クエリ編集"],
        summary="アクセント句から音素長を得る",
    )
    def mora_length(
        accent_phrases: List[AccentPhrase],
        speaker: int,
        core_version: Optional[str] = None,
    ):
        engine = get_engine(core_version)
        return engine.replace_phoneme_length(
            accent_phrases=accent_phrases, speaker_id=speaker
        )

    @app.post(
        "/mora_pitch",
        response_model=List[AccentPhrase],
        tags=["クエリ編集"],
        summary="アクセント句から音高を得る",
    )
    def mora_pitch(
        accent_phrases: List[AccentPhrase],
        speaker: int,
        core_version: Optional[str] = None,
    ):
        engine = get_engine(core_version)
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
    def synthesis(
        query: AudioQuery,
        speaker: int,
        enable_interrogative_upspeak: bool = Query(  # noqa: B008
            default=True,
            description="疑問系のテキストが与えられたら語尾を自動調整する",
        ),
        core_version: Optional[str] = None,
    ):
        engine = get_engine(core_version)
        wave = engine.synthesis(
            query=query,
            speaker_id=speaker,
            enable_interrogative_upspeak=enable_interrogative_upspeak,
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
        speaker: int,
        request: Request,
        core_version: Optional[str] = None,
    ):
        if not args.enable_cancellable_synthesis:
            raise HTTPException(
                status_code=404,
                detail="実験的機能はデフォルトで無効になっています。使用するには引数を指定してください。",
            )
        f_name = cancellable_engine._synthesis_impl(
            query=query,
            speaker_id=speaker,
            request=request,
            core_version=core_version,
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
        queries: List[AudioQuery],
        speaker: int,
        core_version: Optional[str] = None,
    ):
        engine = get_engine(core_version)
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
                        zip_file.writestr(f"{str(i + 1).zfill(3)}.wav", wav_file.read())

        return FileResponse(
            f.name,
            media_type="application/zip",
            background=BackgroundTask(delete_file, f.name),
        )

    @app.post(
        "/morphable_targets",
        response_model=List[Dict[str, MorphableTargetInfo]],
        tags=["音声合成"],
        summary="指定した話者に対してエンジン内の話者がモーフィングが可能か判定する",
    )
    def morphable_targets(
        base_speakers: List[int],
        core_version: Optional[str] = None,
    ):
        """
        指定されたベース話者に対してエンジン内の各話者がモーフィング機能を利用可能か返します。
        モーフィングの許可/禁止は`/speakers`の`speaker.supported_features.synthesis_morphing`に記載されています。
        プロパティが存在しない場合は、モーフィングが許可されているとみなします。
        返り値の話者はstring型なので注意。
        """
        engine = get_engine(core_version)

        try:
            speakers = metas_store.load_combined_metas(engine=engine)
            morphable_targets = get_morphable_targets(
                speakers=speakers, base_speakers=base_speakers
            )
            # jsonはint型のキーを持てないので、string型に変換する
            return [
                {str(k): v for k, v in morphable_target.items()}
                for morphable_target in morphable_targets
            ]
        except SpeakerNotFoundError as e:
            raise HTTPException(
                status_code=404, detail=f"該当する話者(speaker={e.speaker})が見つかりません"
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
        summary="2人の話者でモーフィングした音声を合成する",
    )
    def _synthesis_morphing(
        query: AudioQuery,
        base_speaker: int,
        target_speaker: int,
        morph_rate: float = Query(..., ge=0.0, le=1.0),  # noqa: B008
        core_version: Optional[str] = None,
    ):
        """
        指定された2人の話者で音声を合成、指定した割合でモーフィングした音声を得ます。
        モーフィングの割合は`morph_rate`で指定でき、0.0でベースの話者、1.0でターゲットの話者に近づきます。
        """
        engine = get_engine(core_version)

        try:
            speakers = metas_store.load_combined_metas(engine=engine)
            speaker_lookup = construct_lookup(speakers=speakers)
            is_permitted = is_synthesis_morphing_permitted(
                speaker_lookup, base_speaker, target_speaker
            )
            if not is_permitted:
                raise HTTPException(
                    status_code=400,
                    detail="指定された話者ペアでのモーフィングはできません",
                )
        except SpeakerNotFoundError as e:
            raise HTTPException(
                status_code=404, detail=f"該当する話者(speaker={e.speaker})が見つかりません"
            )

        # 生成したパラメータはキャッシュされる
        morph_param = synthesis_morphing_parameter(
            engine=engine,
            query=query,
            base_speaker=base_speaker,
            target_speaker=target_speaker,
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
    def connect_waves(waves: List[str]):
        """
        base64エンコードされたwavデータを一纏めにし、wavファイルで返します。
        """
        try:
            waves_nparray, sampling_rate = connect_base64_waves(waves)
        except ConnectBase64WavesException as err:
            return HTTPException(status_code=422, detail=str(err))

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

    @app.get("/presets", response_model=List[Preset], tags=["その他"])
    def get_presets():
        """
        エンジンが保持しているプリセットの設定を返します

        Returns
        -------
        presets: List[Preset]
            プリセットのリスト
        """
        try:
            presets = preset_manager.load_presets()
        except PresetError as err:
            raise HTTPException(status_code=422, detail=str(err))
        return presets

    @app.post("/add_preset", response_model=int, tags=["その他"])
    def add_preset(preset: Preset):
        """
        新しいプリセットを追加します

        Parameters
        -------
        preset: Preset
            新しいプリセット。
            プリセットIDが既存のものと重複している場合は、新規のプリセットIDが採番されます。

        Returns
        -------
        id: int
            追加したプリセットのプリセットID
        """
        try:
            id = preset_manager.add_preset(preset)
        except PresetError as err:
            raise HTTPException(status_code=422, detail=str(err))
        return id

    @app.post("/update_preset", response_model=int, tags=["その他"])
    def update_preset(preset: Preset):
        """
        既存のプリセットを更新します

        Parameters
        -------
        preset: Preset
            更新するプリセット。
            プリセットIDが更新対象と一致している必要があります。

        Returns
        -------
        id: int
            更新したプリセットのプリセットID
        """
        try:
            id = preset_manager.update_preset(preset)
        except PresetError as err:
            raise HTTPException(status_code=422, detail=str(err))
        return id

    @app.post("/delete_preset", status_code=204, tags=["その他"])
    def delete_preset(id: int):
        """
        既存のプリセットを削除します

        Parameters
        -------
        id: int
            削除するプリセットのプリセットID

        """
        try:
            preset_manager.delete_preset(id)
        except PresetError as err:
            raise HTTPException(status_code=422, detail=str(err))
        return Response(status_code=204)

    @app.get("/version", tags=["その他"])
    def version() -> str:
        return __version__

    @app.get("/core_versions", response_model=List[str], tags=["その他"])
    def core_versions() -> List[str]:
        return Response(
            content=json.dumps(list(synthesis_engines.keys())),
            media_type="application/json",
        )

    @app.get("/speakers", response_model=List[Speaker], tags=["その他"])
    def speakers(
        core_version: Optional[str] = None,
    ):
        engine = get_engine(core_version)
        return metas_store.load_combined_metas(engine=engine)

    @app.get("/speaker_info", response_model=SpeakerInfo, tags=["その他"])
    def speaker_info(speaker_uuid: str, core_version: Optional[str] = None):
        """
        指定されたspeaker_uuidに関する情報をjson形式で返します。
        画像や音声はbase64エンコードされたものが返されます。

        Returns
        -------
        ret_data: SpeakerInfo
        """
        speakers = json.loads(get_engine(core_version).speakers)
        for i in range(len(speakers)):
            if speakers[i]["speaker_uuid"] == speaker_uuid:
                speaker = speakers[i]
                break
        else:
            raise HTTPException(status_code=404, detail="該当する話者が見つかりません")

        try:
            policy = (root_dir / f"speaker_info/{speaker_uuid}/policy.md").read_text(
                "utf-8"
            )
            portrait = b64encode_str(
                (root_dir / f"speaker_info/{speaker_uuid}/portrait.png").read_bytes()
            )
            style_infos = []
            for style in speaker["styles"]:
                id = style["id"]
                icon = b64encode_str(
                    (
                        root_dir / f"speaker_info/{speaker_uuid}/icons/{id}.png"
                    ).read_bytes()
                )
                style_portrait_path = (
                    root_dir / f"speaker_info/{speaker_uuid}/portraits/{id}.png"
                )
                style_portrait = (
                    b64encode_str(style_portrait_path.read_bytes())
                    if style_portrait_path.exists()
                    else None
                )
                voice_samples = [
                    b64encode_str(
                        (
                            root_dir
                            / "speaker_info/{}/voice_samples/{}_{}.wav".format(
                                speaker_uuid, id, str(j + 1).zfill(3)
                            )
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
            raise HTTPException(status_code=500, detail="追加情報が見つかりませんでした")

        ret_data = {"policy": policy, "portrait": portrait, "style_infos": style_infos}
        return ret_data

    @app.get(
        "/downloadable_libraries",
        response_model=List[DownloadableLibrary],
        tags=["音声ライブラリ管理"],
    )
    def downloadable_libraries():
        """
        ダウンロード可能な音声ライブラリの情報を返します。

        Returns
        -------
        ret_data: List[DownloadableLibrary]
        """
        manifest = engine_manifest_loader.load_manifest()
        if not manifest.supported_features.manage_library:
            raise HTTPException(status_code=404, detail="この機能は実装されていません")
        return library_manager.downloadable_libraries()

    @app.get(
        "/installed_libraries",
        response_model=List[DownloadableLibrary],
        tags=["音声ライブラリ管理"],
    )
    def installed_libraries():
        """
        インストールした音声ライブラリの情報を返します。

        Returns
        -------
        ret_data: List[DownloadableLibrary]
        """
        manifest = engine_manifest_loader.load_manifest()
        if not manifest.supported_features.manage_library:
            raise HTTPException(status_code=404, detail="この機能は実装されていません")
        return library_manager.installed_libraries()

    @app.post(
        "/install_library/{library_uuid}",
        status_code=204,
        tags=["音声ライブラリ管理"],
    )
    async def install_library(library_uuid: str, request: Request):
        """
        音声ライブラリをインストールします。
        音声ライブラリのZIPファイルをリクエストボディとして送信してください。

        Parameters
        ----------
        library_uuid: str
            音声ライブラリのID
        """
        manifest = engine_manifest_loader.load_manifest()
        if not manifest.supported_features.manage_library:
            raise HTTPException(status_code=404, detail="この機能は実装されていません")
        archive = BytesIO(await request.body())
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, library_manager.install_library, library_uuid, archive
        )
        return Response(status_code=204)

    @app.post("/initialize_speaker", status_code=204, tags=["その他"])
    def initialize_speaker(
        speaker: int,
        skip_reinit: bool = Query(  # noqa: B008
            False, description="既に初期化済みの話者の再初期化をスキップするかどうか"
        ),
        core_version: Optional[str] = None,
    ):
        """
        指定されたspeaker_idの話者を初期化します。
        実行しなくても他のAPIは使用できますが、初回実行時に時間がかかることがあります。
        """
        engine = get_engine(core_version)
        engine.initialize_speaker_synthesis(speaker_id=speaker, skip_reinit=skip_reinit)
        return Response(status_code=204)

    @app.get("/is_initialized_speaker", response_model=bool, tags=["その他"])
    def is_initialized_speaker(speaker: int, core_version: Optional[str] = None):
        """
        指定されたspeaker_idの話者が初期化されているかどうかを返します。
        """
        engine = get_engine(core_version)
        return engine.is_initialized_speaker_synthesis(speaker)

    @app.get("/user_dict", response_model=Dict[str, UserDictWord], tags=["ユーザー辞書"])
    def get_user_dict_words():
        """
        ユーザー辞書に登録されている単語の一覧を返します。
        単語の表層形(surface)は正規化済みの物を返します。

        Returns
        -------
        Dict[str, UserDictWord]
            単語のUUIDとその詳細
        """
        try:
            return read_dict()
        except Exception:
            traceback.print_exc()
            raise HTTPException(status_code=422, detail="辞書の読み込みに失敗しました。")

    @app.post("/user_dict_word", response_model=str, tags=["ユーザー辞書"])
    def add_user_dict_word(
        surface: str,
        pronunciation: str,
        accent_type: int,
        word_type: Optional[WordTypes] = None,
        priority: Optional[conint(ge=MIN_PRIORITY, le=MAX_PRIORITY)] = None,
    ):
        """
        ユーザー辞書に言葉を追加します。

        Parameters
        ----------
        surface : str
            言葉の表層形
        pronunciation: str
            言葉の発音（カタカナ）
        accent_type: int
            アクセント型（音が下がる場所を指す）
        word_type: WordTypes, optional
            PROPER_NOUN（固有名詞）、COMMON_NOUN（普通名詞）、VERB（動詞）、ADJECTIVE（形容詞）、SUFFIX（語尾）のいずれか
        priority: int, optional
            単語の優先度（0から10までの整数）
            数字が大きいほど優先度が高くなる
            1から9までの値を指定することを推奨
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
            raise HTTPException(status_code=422, detail="パラメータに誤りがあります。\n" + str(e))
        except Exception:
            traceback.print_exc()
            raise HTTPException(status_code=422, detail="ユーザー辞書への追加に失敗しました。")

    @app.put("/user_dict_word/{word_uuid}", status_code=204, tags=["ユーザー辞書"])
    def rewrite_user_dict_word(
        surface: str,
        pronunciation: str,
        accent_type: int,
        word_uuid: str,
        word_type: Optional[WordTypes] = None,
        priority: Optional[conint(ge=MIN_PRIORITY, le=MAX_PRIORITY)] = None,
    ):
        """
        ユーザー辞書に登録されている言葉を更新します。

        Parameters
        ----------
        surface : str
            言葉の表層形
        pronunciation: str
            言葉の発音（カタカナ）
        accent_type: int
            アクセント型（音が下がる場所を指す）
        word_uuid: str
            更新する言葉のUUID
        word_type: WordTypes, optional
            PROPER_NOUN（固有名詞）、COMMON_NOUN（普通名詞）、VERB（動詞）、ADJECTIVE（形容詞）、SUFFIX（語尾）のいずれか
        priority: int, optional
            単語の優先度（0から10までの整数）
            数字が大きいほど優先度が高くなる
            1から9までの値を指定することを推奨
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
            raise HTTPException(status_code=422, detail="パラメータに誤りがあります。\n" + str(e))
        except Exception:
            traceback.print_exc()
            raise HTTPException(status_code=422, detail="ユーザー辞書の更新に失敗しました。")

    @app.delete("/user_dict_word/{word_uuid}", status_code=204, tags=["ユーザー辞書"])
    def delete_user_dict_word(word_uuid: str):
        """
        ユーザー辞書に登録されている言葉を削除します。

        Parameters
        ----------
        word_uuid: str
            削除する言葉のUUID
        """
        try:
            delete_word(word_uuid=word_uuid)
            return Response(status_code=204)
        except HTTPException:
            raise
        except Exception:
            traceback.print_exc()
            raise HTTPException(status_code=422, detail="ユーザー辞書の更新に失敗しました。")

    @app.post("/import_user_dict", status_code=204, tags=["ユーザー辞書"])
    def import_user_dict_words(
        import_dict_data: Dict[str, UserDictWord], override: bool
    ):
        """
        他のユーザー辞書をインポートします。

        Parameters
        ----------
        import_dict_data: Dict[str, UserDictWord]
            インポートするユーザー辞書のデータ
        override: bool
            重複したエントリがあった場合、上書きするかどうか
        """
        try:
            import_user_dict(dict_data=import_dict_data, override=override)
            return Response(status_code=204)
        except Exception:
            traceback.print_exc()
            raise HTTPException(status_code=422, detail="ユーザー辞書のインポートに失敗しました。")

    @app.get("/supported_devices", response_model=SupportedDevicesInfo, tags=["その他"])
    def supported_devices(
        core_version: Optional[str] = None,
    ):
        supported_devices = get_engine(core_version).supported_devices
        if supported_devices is None:
            raise HTTPException(status_code=422, detail="非対応の機能です。")
        return Response(
            content=supported_devices,
            media_type="application/json",
        )

    @app.get("/engine_manifest", response_model=EngineManifest, tags=["その他"])
    def engine_manifest():
        return engine_manifest_loader.load_manifest()

    @app.get("/setting", response_class=HTMLResponse, tags=["設定"])
    def setting_get(request: Request):
        settings = setting_loader.load_setting_file()

        cors_policy_mode = settings.cors_policy_mode
        allow_origin = settings.allow_origin

        if allow_origin is None:
            allow_origin = ""

        return setting_ui_template.TemplateResponse(
            "ui.html",
            {
                "request": request,
                "cors_policy_mode": cors_policy_mode,
                "allow_origin": allow_origin,
            },
        )

    @app.post("/setting", response_class=HTMLResponse, tags=["設定"])
    def setting_post(
        request: Request,
        cors_policy_mode: Optional[str] = Form(None),  # noqa: B008
        allow_origin: Optional[str] = Form(None),  # noqa: B008
    ):
        settings = Setting(
            cors_policy_mode=cors_policy_mode,
            allow_origin=allow_origin,
        )

        # 更新した設定へ上書き
        setting_loader.dump_setting_file(settings)

        if allow_origin is None:
            allow_origin = ""

        return setting_ui_template.TemplateResponse(
            "ui.html",
            {
                "request": request,
                "cors_policy_mode": cors_policy_mode,
                "allow_origin": allow_origin,
            },
        )

    return app


if __name__ == "__main__":
    multiprocessing.freeze_support()

    output_log_utf8 = os.getenv("VV_OUTPUT_LOG_UTF8", default="")
    if output_log_utf8 == "1":
        set_output_log_utf8()
    elif not (output_log_utf8 == "" or output_log_utf8 == "0"):
        print(
            "WARNING:  invalid VV_OUTPUT_LOG_UTF8 environment variable value",
            file=sys.stderr,
        )

    default_cors_policy_mode = CorsPolicyMode.localapps

    parser = argparse.ArgumentParser(description="VOICEVOX のエンジンです。")
    parser.add_argument(
        "--host", type=str, default="127.0.0.1", help="接続を受け付けるホストアドレスです。"
    )
    parser.add_argument("--port", type=int, default=50021, help="接続を受け付けるポート番号です。")
    parser.add_argument(
        "--use_gpu", action="store_true", help="指定するとGPUを使って音声合成するようになります。"
    )
    parser.add_argument(
        "--voicevox_dir", type=Path, default=None, help="VOICEVOXのディレクトリパスです。"
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
        help="指定するとVOICEVOX COREを使わずモックで音声合成を行います。",
    )
    parser.add_argument(
        "--enable_cancellable_synthesis",
        action="store_true",
        help="指定すると音声合成を途中でキャンセルできるようになります。",
    )
    parser.add_argument(
        "--init_processes",
        type=int,
        default=2,
        help="cancellable_synthesis機能の初期化時に生成するプロセス数です。",
    )
    parser.add_argument(
        "--load_all_models", action="store_true", help="指定すると起動時に全ての音声合成モデルを読み込みます。"
    )

    # 引数へcpu_num_threadsの指定がなければ、環境変数をロールします。
    # 環境変数にもない場合は、Noneのままとします。
    # VV_CPU_NUM_THREADSが空文字列でなく数値でもない場合、エラー終了します。
    parser.add_argument(
        "--cpu_num_threads",
        type=int,
        default=os.getenv("VV_CPU_NUM_THREADS") or None,
        help=(
            "音声合成を行うスレッド数です。指定しないと、代わりに環境変数VV_CPU_NUM_THREADSの値が使われます。"
            "VV_CPU_NUM_THREADSが空文字列でなく数値でもない場合はエラー終了します。"
        ),
    )

    parser.add_argument(
        "--output_log_utf8",
        action="store_true",
        help=(
            "指定するとログ出力をUTF-8でおこないます。指定しないと、代わりに環境変数 VV_OUTPUT_LOG_UTF8 の値が使われます。"
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
        ),
    )

    parser.add_argument(
        "--allow_origin", nargs="*", help="許可するオリジンを指定します。スペースで区切ることで複数指定できます。"
    )

    parser.add_argument(
        "--setting_file", type=Path, default=USER_SETTING_PATH, help="設定ファイルを指定できます。"
    )

    args = parser.parse_args()

    if args.output_log_utf8:
        set_output_log_utf8()

    cpu_num_threads: Optional[int] = args.cpu_num_threads

    synthesis_engines = make_synthesis_engines(
        use_gpu=args.use_gpu,
        voicelib_dirs=args.voicelib_dir,
        voicevox_dir=args.voicevox_dir,
        runtime_dirs=args.runtime_dir,
        cpu_num_threads=cpu_num_threads,
        enable_mock=args.enable_mock,
        load_all_models=args.load_all_models,
    )
    assert len(synthesis_engines) != 0, "音声合成エンジンがありません。"
    latest_core_version = get_latest_core_version(versions=synthesis_engines.keys())

    cancellable_engine = None
    if args.enable_cancellable_synthesis:
        cancellable_engine = CancellableEngine(args)

    root_dir = args.voicevox_dir if args.voicevox_dir is not None else engine_root()

    setting_loader = SettingLoader(args.setting_file)

    settings = setting_loader.load_setting_file()

    cors_policy_mode = (
        args.cors_policy_mode
        if args.cors_policy_mode is not None
        else settings.cors_policy_mode
    )

    allow_origin = None
    if args.allow_origin is not None:
        allow_origin = args.allow_origin
    elif settings.allow_origin is not None:
        allow_origin = settings.allow_origin.split(" ")

    uvicorn.run(
        generate_app(
            synthesis_engines,
            latest_core_version,
            setting_loader,
            root_dir=root_dir,
            cors_policy_mode=cors_policy_mode,
            allow_origin=allow_origin,
        ),
        host=args.host,
        port=args.port,
    )
