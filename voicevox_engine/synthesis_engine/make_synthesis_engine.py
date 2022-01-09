import sys
from pathlib import Path
from typing import Optional

from .core_wrapper import CoreWrapper
from .synthesis_engine import SynthesisEngine, SynthesisEngineBase


def make_synthesis_engine(
    use_gpu: bool,
    voicelib_dir: Path,
    voicevox_dir: Optional[Path] = None,
    model_type: Optional[str] = "onnxruntime",
    model_lib_dir: Optional[Path] = None,
    use_mock: Optional[bool] = True,
) -> SynthesisEngineBase:
    """
    音声ライブラリをロードして、音声合成エンジンを生成

    Parameters
    ----------
    use_gpu: bool
        音声ライブラリに GPU を使わせるか否か
    voicelib_dir: Path
        音声ライブラリ自体があるディレクトリ
    voicevox_dir: Path, optional, default=None
        音声ライブラリの Python モジュールがあるディレクトリ
        None のとき、Python 標準のモジュール検索パスのどれかにあるとする
    model_type: str, optional, default="onnxruntime"
        コアで使用するライブラリの名称
    model_lib_dir: Path, optional, default=None
        コアで使用するライブラリのあるディレクトリ
        None のとき、voicevox_dir、それもNoneの場合はカレントディレクトリになる
    use_mock: bool, optional, default=True
        音声ライブラリの読み込みに失敗した際に代わりにmockを使用するか否か
    """

    if model_lib_dir is None:
        if voicevox_dir is None:
            if "__compiled__" in globals():
                model_lib_dir = Path(sys.argv[0]).parent
            else:
                model_lib_dir = Path(__file__).parents[2]
        else:
            model_lib_dir = voicevox_dir
    if not model_lib_dir.is_dir():
        raise Exception("model_lib_dirが不正です")
    has_voicevox_core = True

    voicelib_dir = voicelib_dir.expanduser()
    model_lib_dir = model_lib_dir.expanduser()

    try:
        core = CoreWrapper(use_gpu, voicelib_dir, model_lib_dir, model_type)
    except Exception:
        import traceback

        from ..dev import core

        has_voicevox_core = False

        # 音声ライブラリの Python モジュールをロードできなかった
        traceback.print_exc()
        if use_mock:
            print(
                "Notice: mock-library will be used. Try re-run with valid --voicevox_dir",
                file=sys.stderr,
            )
        else:
            print(
                "Notice: Failed to make synthesis engine. This error will be ignored.",
                file=sys.stderr,
            )

    if has_voicevox_core:
        return SynthesisEngine(
            yukarin_s_forwarder=core.yukarin_s_forward,
            yukarin_sa_forwarder=core.yukarin_sa_forward,
            decode_forwarder=core.decode_forward,
            speakers=core.metas(),
        )

    from ..dev.synthesis_engine import MockSynthesisEngine

    # モックで置き換える
    return MockSynthesisEngine(speakers=core.metas())
