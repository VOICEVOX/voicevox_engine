import json
import sys
from pathlib import Path
from typing import List, Optional

from ..tts_pipeline.tts_engine import CoreAdapter
from ..utility import engine_root, get_save_dir
from .core_wrapper import CoreWrapper, load_runtime_lib

MOCK_VER = "0.0.0"


def initialize_cores(
    use_gpu: bool,
    voicelib_dirs: Optional[List[Path]] = None,
    voicevox_dir: Optional[Path] = None,
    runtime_dirs: Optional[List[Path]] = None,
    cpu_num_threads: Optional[int] = None,
    enable_mock: bool = True,
    load_all_models: bool = False,
) -> dict[str, CoreAdapter]:
    """
    音声ライブラリをロードしてコアを生成

    Parameters
    ----------
    use_gpu: bool
        音声ライブラリに GPU を使わせるか否か
    voicelib_dirs: List[Path], optional, default=None
        音声ライブラリ自体があるディレクトリのリスト
    voicevox_dir: Path, optional, default=None
        コンパイル済みのvoicevox、またはvoicevox_engineがあるディレクトリ
    runtime_dirs: List[Path], optional, default=None
        コアで使用するライブラリのあるディレクトリのリスト
        None のとき、voicevox_dir、カレントディレクトリになる
    cpu_num_threads: int, optional, default=None
        音声ライブラリが、推論に用いるCPUスレッド数を設定する
        Noneのとき、ライブラリ側の挙動により論理コア数の半分か、物理コア数が指定される
    enable_mock: bool, optional, default=True
        コア読み込みに失敗したとき、代わりにmockを使用するかどうか
    load_all_models: bool, optional, default=False
        起動時に全てのモデルを読み込むかどうか
    """
    if cpu_num_threads == 0 or cpu_num_threads is None:
        print(
            "Warning: cpu_num_threads is set to 0. "
            + "( The library leaves the decision to the synthesis runtime )",
            file=sys.stderr,
        )
        cpu_num_threads = 0

    # ディレクトリを設定する
    # 引数による指定を反映する
    if voicevox_dir is not None:
        if voicelib_dirs is not None:
            voicelib_dirs.append(voicevox_dir)
        else:
            voicelib_dirs = [voicevox_dir]
        if runtime_dirs is not None:
            runtime_dirs.append(voicevox_dir)
        else:
            runtime_dirs = [voicevox_dir]
    else:
        root_dir = engine_root()
        if voicelib_dirs is None:
            voicelib_dirs = [root_dir]
        if runtime_dirs is None:
            runtime_dirs = [root_dir]

    # `~`をホームディレクトリのパスに置き換える
    voicelib_dirs = [p.expanduser() for p in voicelib_dirs]
    runtime_dirs = [p.expanduser() for p in runtime_dirs]

    # ランタイムをロードする
    load_runtime_lib(runtime_dirs)

    # コアをロードし `cores` へ登録する
    cores: dict[str, CoreAdapter] = {}

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
        from ..dev.core import MockCoreWrapper

        if MOCK_VER not in cores:
            print("Info: Loading mock.")
            core = MockCoreWrapper()
            cores[MOCK_VER] = CoreAdapter(core)

    return cores
