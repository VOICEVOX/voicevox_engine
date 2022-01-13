import sys
from pathlib import Path
from typing import Optional

from .synthesis_engine import SynthesisEngine, SynthesisEngineBase


def make_synthesis_engine(
    use_gpu: bool,
    voicelib_dir: Path,
    voicevox_dir: Optional[Path] = None,
    cpu_num_threads: Optional[int] = None,
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
    cpu_num_threads: int, optional, default=None
        音声ライブラリが、推論に用いるCPUスレッド数を設定する
        Noneのとき、ライブラリ側の挙動により論理コア数の半分か、物理コア数が指定される
    """

    # Python モジュール検索パスへ追加
    if voicevox_dir is not None:
        print("Notice: --voicevox_dir is " + voicevox_dir.as_posix(), file=sys.stderr)
        if voicevox_dir.exists():
            sys.path.insert(0, str(voicevox_dir))

    has_voicevox_core = True
    try:
        import core
    except ImportError:
        import traceback

        from ..dev import core

        has_voicevox_core = False

        # 音声ライブラリの Python モジュールをロードできなかった
        traceback.print_exc()
        print(
            "Notice: mock-library will be used. Try re-run with valid --voicevox_dir",
            file=sys.stderr,
        )

    if cpu_num_threads == 0:
        print(
            "Warning: cpu_num_threads is set to 0. ( The library leaves the decision to the synthesis runtime )"
        )

    core.initialize(voicelib_dir.as_posix() + "/", use_gpu, cpu_num_threads or 0)

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
