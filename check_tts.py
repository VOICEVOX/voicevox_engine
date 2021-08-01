import argparse
from itertools import product
from pathlib import Path
from typing import List, Optional

import each_cpp_forwarder
import soundfile

from voicevox_engine.forwarder import Forwarder


def run(
    forwarder_dir: Path,
    use_gpu: bool,
    texts: List[str],
    speaker_ids: List[int],
    f0_speaker_id: Optional[int],
    f0_correct: float,
):
    each_cpp_forwarder.initialize("1", "2", "3", use_gpu)

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
    parser.add_argument("--forwarder_dir", type=Path, required=True)
    parser.add_argument("--use_gpu", action="store_true")
    parser.add_argument("--texts", nargs="+", required=True)
    parser.add_argument("--speaker_ids", nargs="+", type=int, required=True)
    parser.add_argument("--f0_speaker_id", type=int)
    parser.add_argument("--f0_correct", type=float, default=0)
    run(**vars(parser.parse_args()))
