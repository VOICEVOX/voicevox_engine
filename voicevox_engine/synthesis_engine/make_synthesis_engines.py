import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

from ..utility import engine_root, get_save_dir
from .core_wrapper import CoreWrapper, load_runtime_lib
from .synthesis_engine import SynthesisEngine, SynthesisEngineBase


def make_synthesis_engines(
    use_gpu: bool,
    voicelib_dirs: Optional[List[Path]] = None,
    voicevox_dir: Optional[Path] = None,
    runtime_dirs: Optional[List[Path]] = None,
    cpu_num_threads: Optional[int] = None,
    enable_mock: bool = True,
    load_all_models: bool = False,
) -> Dict[str, SynthesisEngineBase]:
    """
    音声ライブラリをロードして、音声合成エンジンを生成

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

    voicelib_dirs = [p.expanduser() for p in voicelib_dirs]
    runtime_dirs = [p.expanduser() for p in runtime_dirs]

    load_runtime_lib(runtime_dirs)

    synthesis_engines = {}

    if not enable_mock:

        def load_core_library(core_dir: Path, suppress_error: bool = False):
            """
            指定されたディレクトリにあるコアを読み込む。
            ユーザーディレクトリの場合は存在しないこともあるので、エラーを抑制すると良い。
            """
            try:
                core = CoreWrapper(use_gpu, core_dir, cpu_num_threads, load_all_models)
                metas = json.loads(core.metas())
                core_version = metas[0]["version"]
                print(f"Info: Loading core {core_version}.")
                if core_version in synthesis_engines:
                    print(
                        "Warning: Core loading is skipped because of version duplication.",
                        file=sys.stderr,
                    )
                else:
                    synthesis_engines[core_version] = SynthesisEngine(core=core)
            except Exception:
                if not suppress_error:
                    raise

        for core_dir in voicelib_dirs:
            load_core_library(core_dir)

        # ユーザーディレクトリにあるコアを読み込む
        user_voicelib_dirs = []
        core_libraries_dir = get_save_dir() / "core_libraries"
        core_libraries_dir.mkdir(exist_ok=True)
        user_voicelib_dirs.append(core_libraries_dir)
        for path in core_libraries_dir.glob("*"):
            if not path.is_dir():
                continue
            user_voicelib_dirs.append(path)

        for core_dir in user_voicelib_dirs:
            load_core_library(core_dir, suppress_error=True)

    else:
        # モック追加
        from ..dev.core import metas as mock_metas
        from ..dev.core import supported_devices as mock_supported_devices
        from ..dev.synthesis_engine import MockSynthesisEngine

        if "0.0.0" not in synthesis_engines:
            print("Info: Loading mock.")
            synthesis_engines["0.0.0"] = MockSynthesisEngine(
                speakers=mock_metas(), supported_devices=mock_supported_devices()
            )

    return synthesis_engines
