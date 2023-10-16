"""
ビルド結果をテストする
"""
import argparse
import json
import time
from io import BytesIO
from pathlib import Path
from subprocess import Popen
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import soundfile

base_url = "http://127.0.0.1:50021/"


def test_release_build(dist_dir: Path, skip_run_process: bool) -> None:
    run_file = dist_dir / "run"
    if not run_file.exists():
        run_file = dist_dir / "run.exe"

    # 起動
    process = None
    if not skip_run_process:
        process = Popen([run_file.absolute()], cwd=dist_dir)
        time.sleep(60)  # 待機

    # バージョン取得テスト
    req = Request(base_url + "version")
    with urlopen(req) as res:
        assert len(res.read()) > 0

    # テキスト -> クエリ
    text = "こんにちは、音声合成の世界へようこそ"
    req = Request(
        base_url + "audio_query?" + urlencode({"style_id": "1", "text": text}),
        method="POST",
    )
    with urlopen(req) as res:
        query = json.loads(res.read().decode("utf-8"))

    # クエリ -> 音声
    req = Request(base_url + "synthesis?style_id=1", method="POST")
    req.add_header("Content-Type", "application/json")
    req.data = json.dumps(query).encode("utf-8")
    with urlopen(req) as res:
        wave = res.read()
    soundfile.read(BytesIO(wave))

    # エンジンマニフェスト
    req = Request(base_url + "engine_manifest", method="GET")
    with urlopen(req) as res:
        manifest = json.loads(res.read().decode("utf-8"))
        assert "uuid" in manifest

    if not skip_run_process:
        # プロセスが稼働中であることを確認
        assert process.poll() is None

        # 停止
        process.terminate()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist_dir", type=Path, default=Path("dist/"))
    parser.add_argument("--skip_run_process", action="store_true")
    args = parser.parse_args()
    test_release_build(dist_dir=args.dist_dir, skip_run_process=args.skip_run_process)
