import argparse
import multiprocessing
import os
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from io import TextIOWrapper
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from voicevox_engine import __version__
from voicevox_engine.app.dependencies import deprecated_mutable_api
from voicevox_engine.app.middlewares import configure_middlewares
from voicevox_engine.app.openapi_schema import configure_openapi_schema
from voicevox_engine.app.routers.engine_info import generate_engine_info_router
from voicevox_engine.app.routers.library import generate_library_router
from voicevox_engine.app.routers.morphing import generate_morphing_router
from voicevox_engine.app.routers.preset import generate_preset_router
from voicevox_engine.app.routers.setting import generate_setting_router
from voicevox_engine.app.routers.speaker import generate_speaker_router
from voicevox_engine.app.routers.tts_pipeline import generate_tts_pipeline_router
from voicevox_engine.app.routers.user_dict import generate_user_dict_router
from voicevox_engine.cancellable_engine import CancellableEngine
from voicevox_engine.core.core_adapter import CoreAdapter
from voicevox_engine.core.core_initializer import initialize_cores
from voicevox_engine.engine_manifest.EngineManifestLoader import EngineManifestLoader
from voicevox_engine.library_manager import LibraryManager
from voicevox_engine.metas.MetasStore import MetasStore
from voicevox_engine.preset.PresetManager import PresetManager
from voicevox_engine.setting.Setting import CorsPolicyMode
from voicevox_engine.setting.SettingLoader import USER_SETTING_PATH, SettingHandler
from voicevox_engine.tts_pipeline.tts_engine import (
    TTSEngine,
    make_tts_engines_from_cores,
)
from voicevox_engine.user_dict.user_dict import update_dict
from voicevox_engine.utility.core_version_utility import get_latest_version
from voicevox_engine.utility.path_utility import engine_root, get_save_dir
from voicevox_engine.utility.run_utility import decide_boolean_from_env


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
    app = configure_middlewares(app, cors_policy_mode, allow_origin)

    if disable_mutable_api:
        deprecated_mutable_api.enable = False

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

    app.include_router(
        generate_tts_pipeline_router(
            get_engine, get_core, preset_manager, cancellable_engine
        )
    )
    app.include_router(generate_morphing_router(get_engine, get_core, metas_store))
    app.include_router(generate_preset_router(preset_manager))
    app.include_router(generate_speaker_router(get_core, metas_store, root_dir))
    if engine_manifest_data.supported_features.manage_library:
        app.include_router(
            generate_library_router(engine_manifest_data, library_manager)
        )
    app.include_router(generate_user_dict_router())
    app.include_router(
        generate_engine_info_router(get_core, cores, engine_manifest_data)
    )
    app.include_router(
        generate_setting_router(
            setting_loader, engine_manifest_data, setting_ui_template
        )
    )

    @app.get("/", response_class=HTMLResponse, tags=["その他"])
    async def get_portal() -> str:
        """ポータルページを返します。"""
        engine_name = engine_manifest_data.name

        return f"""
        <html>
            <head>
                <title>{engine_name}</title>
            </head>
            <body>
                <h1>{engine_name}</h1>
                {engine_name} へようこそ！
                <ul>
                    <li><a href='/setting'>設定</a></li>
                    <li><a href='/docs'>API ドキュメント</a></li>
        </ul></body></html>
        """

    app = configure_openapi_schema(app)

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
    latest_core_version = get_latest_version(list(tts_engines.keys()))

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
