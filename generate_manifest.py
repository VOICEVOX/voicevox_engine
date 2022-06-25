import base64
import json
import os
from pathlib import Path


def generate_manifest(base: str, icon_path: str) -> dict:
    with open(base, "r") as f:
        manifest = json.load(f)
    manifest["version"] = os.getenv("VOICEVOX_ENGINE_VERSION")
    with open(icon_path, "rb") as f:
        manifest["icon"] = base64.b64encode(f.read()).decode()
    return manifest


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output_path", type=str)
    parser.add_argument("-i", "--icon_path", type=str)
    parser.add_argument("input", type=str, nargs="?")
    args = parser.parse_args()

    output_path = args.output_path
    icon_path = args.icon_path or "manifest_assets/icon.png"
    input_path = args.input or "manifest_assets/manifest.json"

    manifest = generate_manifest(input_path, icon_path)

    # dump
    out = Path(output_path).open("w") if output_path else sys.stdout
    json.dump(
        manifest,
        out,
    )
