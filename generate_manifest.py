import json
import os
from pathlib import Path


def generate_manifest(base: str) -> dict:
    with open(base, "r") as f:
        manifest = json.load(f)
    manifest["version"] = os.getenv("VOICEVOX_ENGINE_VERSION")
    return manifest


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output_path", type=str)
    parser.add_argument("input", type=str, nargs="?")
    args = parser.parse_args()

    output_path = args.output_path
    input_path = args.input or "manifest_assets/manifest.json"

    manifest = generate_manifest(input_path)

    # dump
    out = Path(output_path).open("w") if output_path else sys.stdout
    json.dump(
        manifest,
        out,
    )
