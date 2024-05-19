"""VOICEVOX CORE の初期化"""

import json
import os
import sys
from pathlib import Path

from ..tts_pipeline.tts_engine import CoreAdapter
from ..utility.path_utility import engine_root, get_save_dir
from .core_wrapper import CoreWrapper, load_runtime_lib

MOCK_VER = "0.0.0"


def get_half_logical_cores() -> int:
    logical_cores = os.cpu_count()
    if logical_cores is None:
        return 0
    return logical_cores // 2


def initialize_cores(
    use_gpu: bool,
    voicelib_dirs: list[Path] | None = None,
    voicevox_dir: Path | None = None,
    runtime_dirs: list[Path] | None = None,
    cpu_num_threads: int | None = None,
    enable_mock: bool = True,
    load_all_models: bool = False,
) -> dict[str, CoreAdapter]:
    """
    音声ライブラリをロードしてコアを生成

    Parameters
    ----------
    use_gpu: bool
        音声ライブラリに GPU を使わせるか否か
    voicelib_dirs:
        音声ライブラリ自体があるディレクトリのリスト
    voicevox_dir:
        コンパイル済みのvoicevox、またはvoicevox_engineがあるディレクトリ
    runtime_dirs:
        コアで使用するライブラリのあるディレクトリのリスト
        None のとき、voicevox_dir、カレントディレクトリになる
    cpu_num_threads:
        音声ライブラリが、推論に用いるCPUスレッド数を設定する
        Noneのとき、論理コア数の半分が指定される
    enable_mock:
        コア読み込みに失敗したとき、代わりにmockを使用するかどうか
    load_all_models:
        起動時に全てのモデルを読み込むかどうか
    """
    if cpu_num_threads == 0 or cpu_num_threads is None:
        print(
            "Warning: cpu_num_threads is set to 0. "
            + "Setting it to half of the logical cores.",
            file=sys.stderr,
        )
        cpu_num_threads = get_half_logical_cores()

    root_dir = engine_root()

    # 引数による指定を反映し、無ければ `root_dir` とする
    runtime_dirs = runtime_dirs or []
    runtime_dirs += [voicevox_dir] if voicevox_dir else []
    runtime_dirs = runtime_dirs or [root_dir]
    runtime_dirs = [p.expanduser() for p in runtime_dirs]
    # ランタイムをロードする
    load_runtime_lib(runtime_dirs)

    # コアをロードし `cores` へ登録する
    cores: dict[str, CoreAdapter] = {}

    # 引数による指定を反映し、無ければ `root_dir` とする
    voicelib_dirs = voicelib_dirs or []
    voicelib_dirs += [voicevox_dir] if voicevox_dir else []
    voicelib_dirs = voicelib_dirs or [root_dir]
    voicelib_dirs = [p.expanduser() for p in voicelib_dirs]

    if not enable_mock:

        def load_core_library(core_dir: Path, suppress_error: bool = False) -> None:
            """
            指定されたコアをロードし `cores` へ登録する。
            Parameters
            ----------
            core_dir : Path
                直下にコア（共有ライブラリ）が存在するディレクトリ、あるいはその候補
            suppress_error: bool
                エラーを抑制する。`core_dir` がコア候補であることを想定。
            """
            # 指定されたコアをロードし登録する
            try:
                # コアをロードする
                core = CoreWrapper(use_gpu, core_dir, cpu_num_threads, load_all_models)
                # コアを登録する
                metas = json.loads(core.metas())
                core_version = metas[0]["version"]
                print(f"Info: Loading core {core_version}.")
                if core_version in cores:
                    print(
                        "Warning: Core loading is skipped because of version duplication.",
                        file=sys.stderr,
                    )
                else:
                    cores[core_version] = CoreAdapter(core)
            except Exception:
                # コアでなかった場合のエラーを抑制する
                if not suppress_error:
                    raise

        # `voicelib_dirs` 下のコアをロードし登録する
        for core_dir in voicelib_dirs:
            load_core_library(core_dir)

        # ユーザーディレクトリ下のコアをロードし登録する
        # コア候補を列挙する
        user_voicelib_dirs = []
        core_libraries_dir = get_save_dir() / "core_libraries"
        core_libraries_dir.mkdir(exist_ok=True)
        user_voicelib_dirs.append(core_libraries_dir)
        for path in core_libraries_dir.glob("*"):
            if not path.is_dir():
                continue
            user_voicelib_dirs.append(path)
        # コア候補をロードし登録する。候補がコアで無かった場合のエラーを抑制する。
        for core_dir in user_voicelib_dirs:
            load_core_library(core_dir, suppress_error=True)

    else:
        # モック追加
        from ..dev.core.mock import MockCoreWrapper

        if MOCK_VER not in cores:
            print("Info: Loading mock.")
            core = MockCoreWrapper()
            cores[MOCK_VER] = CoreAdapter(core)

    return cores
