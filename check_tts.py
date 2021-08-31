import argparse
import sys
from itertools import product
from pathlib import Path
from typing import List, Optional

import soundfile

from voicevox_engine.forwarder import Forwarder


def run(
    voicevox_dir: Optional[Path],
    voicelib_dir: Optional[Path],
    use_gpu: bool,
    texts: List[str],
    speaker_ids: List[int],
    f0_speaker_id: Optional[int],
    f0_correct: float,
) -> None:
    # Python モジュール検索パスへ追加
    if voicevox_dir is not None:
        print("Notice: --voicevox_dir is " + voicevox_dir.as_posix(), file=sys.stderr)
        if voicevox_dir.exists():
            sys.path.insert(0, str(voicevox_dir))

    try:
        import each_cpp_forwarder
    except ImportError:
        from voicevox_engine.dev import each_cpp_forwarder

        # 音声ライブラリの Python モジュールをロードできなかった
        print(
            "Notice: mock-library will be used. Try re-run with valid --voicevox_dir",  # noqa
            file=sys.stderr,
        )

    if voicelib_dir is None:
        voicelib_dir = Path(each_cpp_forwarder.__file__).parent

    each_cpp_forwarder.initialize(
        voicelib_dir.as_posix() + "/",
        "1",
        "2",
        "3",
        use_gpu,
    )

    forwarder = Forwarder(
        yukarin_s_forwarder=each_cpp_forwarder.yukarin_s_forward,
        yukarin_sa_forwarder=each_cpp_forwarder.yukarin_sa_forward,
        decode_forwarder=each_cpp_forwarder.decode_forward,
    )

    for text, speaker_id in list(product(texts, speaker_ids)):
        wave = forwarder.forward(
            text=text,
            speaker_id=speaker_id,
            f0_speaker_id=f0_speaker_id if f0_speaker_id is not None else speaker_id,
            f0_correct=f0_correct,
        )

        soundfile.write(f"{text}-{speaker_id}.wav", data=wave, samplerate=24000)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--voicevox_dir", type=Path, default=None)
    parser.add_argument("--voicelib_dir", type=Path, default=None)
    parser.add_argument("--use_gpu", action="store_true")
    parser.add_argument("--texts", nargs="+", required=True)
    parser.add_argument("--speaker_ids", nargs="+", type=int, required=True)
    parser.add_argument("--f0_speaker_id", type=int)
    parser.add_argument("--f0_correct", type=float, default=0)
    run(**vars(parser.parse_args()))
