import argparse
import multiprocessing
import os
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from io import TextIOWrapper
from pathlib import Path
from typing import TypeVar

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.templating import Jinja2Templates

from voicevox_engine import __version__
from voicevox_engine.app.dependencies import deprecated_mutable_api
from voicevox_engine.app.middlewares import configure_middlewares
from voicevox_engine.app.openapi_schema import configure_openapi_schema
from voicevox_engine.app.routers import (
    engine_info,
    library,
    morphing,
    preset,
    setting,
    speaker,
    tts_pipeline,
    user_dict,
)
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
from voicevox_engine.utility.core_version_utility import get_latest_core_version
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
    root_dir: Path | None = None,
    cors_policy_mode: CorsPolicyMode = CorsPolicyMode.localapps,
    allow_origin: list[str] | None = None,
    disable_mutable_api: bool = False,
) -> FastAPI:
    """ASGI 'application' 仕様に準拠した VOICEVOX ENGINE アプリケーションインスタンスを生成する。"""
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

    # @app.on_event("startup")
    # async def start_catch_disconnection():
    #     if cancellable_engine is not None:
    #         loop = asyncio.get_event_loop()
    #         _ = loop.create_task(cancellable_engine.catch_disconnection())

    def get_engine(core_version: str | None) -> TTSEngine:
        if core_version is None:
            return tts_engines[latest_core_version]
        if core_version in tts_engines:
            return tts_engines[core_version]
        raise HTTPException(status_code=422, detail="不明なバージョンです")

    def get_core(core_version: str | None) -> CoreAdapter:
        """指定したバージョンのコアを取得する"""
        if core_version is None:
            return cores[latest_core_version]
        if core_version in cores:
            return cores[core_version]
        raise HTTPException(status_code=422, detail="不明なバージョンです")

    app.include_router(
        tts_pipeline.generate_router(
            get_engine, get_core, preset_manager, cancellable_engine
        )
    )

    app.include_router(morphing.generate_router(get_engine, get_core, metas_store))
    app.include_router(preset.generate_router(preset_manager))

    app.include_router(speaker.generate_router(get_core, metas_store, root_dir))

    if engine_manifest_data.supported_features.manage_library:
        app.include_router(
            library.generate_router(engine_manifest_data, library_manager)
        )

    app.include_router(user_dict.generate_router())

    app.include_router(
        engine_info.generate_router(get_core, cores, engine_manifest_data)
    )

    app.include_router(
        setting.generate_router(
            setting_loader, engine_manifest_data, setting_ui_template
        )
    )

    app = configure_openapi_schema(app)

    return app


T = TypeVar("T")


def select_first_not_none(candidates: list[T | None]) -> T:
    """None でない最初の値を取り出す。全て None の場合はエラーを送出する。"""
    for candidate in candidates:
        if candidate is not None:
            return candidate
    raise RuntimeError("すべての候補値が None です")


S = TypeVar("S")


def select_first_not_none_or_none(candidates: list[S | None]) -> S | None:
    """None でない最初の値を取り出そうとし、全て None の場合は None を返す。"""
    for candidate in candidates:
        if candidate is not None:
            return candidate
    return None


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

    # NOTE: 型検査のため Any 値に対して明示的に型を付ける
    arg_cors_policy_mode: CorsPolicyMode | None = args.cors_policy_mode
    arg_allow_origin: list[str] | None = args.allow_origin
    arg_preset_path: Path | None = args.preset_file
    arg_disable_mutable_api: bool = args.disable_mutable_api

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

    setting_loader = SettingHandler(args.setting_file)
    settings = setting_loader.load()

    # 複数方式で指定可能な場合、優先度は「引数 > 環境変数 > 設定ファイル > デフォルト値」

    root_dir = select_first_not_none([voicevox_dir, engine_root()])

    cors_policy_mode = select_first_not_none(
        [arg_cors_policy_mode, settings.cors_policy_mode]
    )

    setting_allow_origin = None
    if settings.allow_origin is not None:
        setting_allow_origin = settings.allow_origin.split(" ")
    allow_origin = select_first_not_none_or_none(
        [arg_allow_origin, setting_allow_origin]
    )

    env_preset_path_str = os.getenv("VV_PRESET_FILE")
    if env_preset_path_str is not None and len(env_preset_path_str) != 0:
        env_preset_path = Path(env_preset_path_str)
    else:
        env_preset_path = None
    root_preset_path = root_dir / "presets.yaml"
    preset_path = select_first_not_none(
        [arg_preset_path, env_preset_path, root_preset_path]
    )
    # ファイルの存在に関わらず指定されたパスをプリセットファイルとして使用する
    preset_manager = PresetManager(preset_path)

    if arg_disable_mutable_api:
        disable_mutable_api = True
    else:
        disable_mutable_api = decide_boolean_from_env("VV_DISABLE_MUTABLE_API")

    # ASGI に準拠した VOICEVOX ENGINE アプリケーションを生成する
    app = generate_app(
        tts_engines,
        cores,
        latest_core_version,
        setting_loader,
        preset_manager,
        cancellable_engine,
        root_dir,
        cors_policy_mode,
        allow_origin,
        disable_mutable_api=disable_mutable_api,
    )

    # VOICEVOX ENGINE サーバーを起動
    # NOTE: デフォルトは ASGI に準拠した HTTP/1.1 サーバー
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
