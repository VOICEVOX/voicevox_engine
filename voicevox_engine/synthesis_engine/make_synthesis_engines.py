import json
import sys
import traceback
from copy import copy
from pathlib import Path
from typing import List, Optional

from ..dev import core as mock_core
from ..dev.synthesis_engine import MockSynthesisEngine
from .core_wrapper import CoreWrapper, load_model_lib
from .synthesis_engine import SynthesisEngine, SynthesisEngineBase


def make_synthesis_engines(
    use_gpu: bool,
    voicelib_dir: Optional[List[Path]] = None,
    voicevox_dir: Optional[Path] = None,
    model_lib_dir: Optional[List[Path]] = None,
    cpu_num_threads: int = 0,
    raise_error: bool = True,
) -> List[SynthesisEngineBase]:
    """
    音声ライブラリをロードして、音声合成エンジンを生成

    Parameters
    ----------
    use_gpu: bool
        音声ライブラリに GPU を使わせるか否か
    voicelib_dir: List[Path], optional, defauld=None
        音声ライブラリ自体があるディレクトリのリスト
    voicevox_dir: Path, optional, default=None
        コンパイル済みのvoicevox、またはvoicevox_engineがあるディレクトリ
    model_lib_dir: List[Path], optional, default=None
        コアで使用するライブラリのあるディレクトリのリスト
        None のとき、voicevox_dir、カレントディレクトリになる
    cpu_num_threads: int, optional, default=None
        音声ライブラリが、推論に用いるCPUスレッド数を設定する
        Noneのとき、ライブラリ側の挙動により論理コア数の半分か、物理コア数が指定される
    raise_error: bool, optional, default=True
        コア読み込みに失敗したときにエラーを送出するかどうか
        Falseだと代わりにmockが使用される
    """
    if cpu_num_threads == 0:
        print(
            "Warning: cpu_num_threads is set to 0. "
            + "( The library leaves the decision to the synthesis runtime )",
            file=sys.stderr,
        )
    if "__compiled__" in globals():
        root_dir = Path(sys.argv[0]).parent
    else:
        root_dir = Path(__file__).parents[2]

    if voicevox_dir is not None:
        if voicelib_dir is not None:
            voicelib_dir.append(voicevox_dir)
        else:
            voicelib_dir = [voicevox_dir]
        if model_lib_dir is not None:
            model_lib_dir.append(model_lib_dir)
        else:
            model_lib_dir = [model_lib_dir]
    else:
        if voicelib_dir is None:
            voicelib_dir = [copy(root_dir)]
        if model_lib_dir is None:
            model_lib_dir = [copy(root_dir)]

    voicelib_dir = [p.expanduser() for p in voicelib_dir]
    model_lib_dir = [p.expanduser() for p in model_lib_dir]

    load_model_lib(model_lib_dir)
    synthesis_engines = {}
    for core_dir in voicelib_dir:
        try:
            core = CoreWrapper(use_gpu, core_dir, cpu_num_threads)
            metas = json.loads(core.metas())
            if "version" in metas[0]:
                core_version = metas[0]["version"]
            else:
                core_version = "0.5.2"
            if core_version in synthesis_engines:
                print(
                    "Warning: Core loading is skipped because of version duplication.",
                    file=sys.stderr,
                )
                continue
            synthesis_engines[core_version] = SynthesisEngine(
                yukarin_s_forwarder=core.yukarin_s_forward,
                yukarin_sa_forwarder=core.yukarin_sa_forward,
                decode_forwarder=core.decode_forward,
                speakers=metas,
            )
        except Exception:
            if raise_error:
                raise
            traceback.print_exc()
            print(
                "Notice: mock-library will be used. Try re-run with valid --voicevox_dir",
                file=sys.stderr,
            )
            if "0.0.0" not in synthesis_engines:
                synthesis_engines["0.0.0"] = MockSynthesisEngine(
                    speakers=mock_core.metas()
                )
