"""
ビルド結果をテストする
"""
import argparse
import json
import time
from io import BytesIO
from pathlib import Path
from subprocess import Popen
from typing import Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import soundfile

base_url = "http://localhost:50021/"


def test_release_build(dist_dir: Path) -> None:
    run_file = dist_dir / "run"
    if not run_file.exists():
        run_file = dist_dir / "run.exe"

    error: Optional[Exception] = None

    try:
        # 起動
        process = Popen([run_file.absolute()], cwd=dist_dir)
        time.sleep(30)  # 待機

        # バージョン取得テスト
        req = Request(base_url + "version")
        with urlopen(req) as res:
            assert len(res.read()) > 0

        # テキスト -> クエリ
        text = "こんにちは、音声合成の世界へようこそ"
        req = Request(
            base_url + "audio_query?" + urlencode({"speaker": "1", "text": text}),
            method="POST",
        )
        with urlopen(req) as res:
            query = json.loads(res.read().decode("utf-8"))

        # クエリ -> 音声
        req = Request(base_url + "synthesis?speaker=1", method="POST")
        req.add_header("Content-Type", "application/json")
        req.data = json.dumps(query).encode("utf-8")
        with urlopen(req) as res:
            wave = res.read()
        soundfile.read(BytesIO(wave))

        # プロセスが稼働中であることを確認
        assert process.poll() is None

    except Exception as e:
        stdout, stderr = process.communicate()
        print("--engine stdout--")
        print(stdout.decode("utf-8"))
        print("--engine stderr--")
        print(stderr.decode("utf-8"))

        error = e

    # 停止
    process.kill()

    if error:
        raise error


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist_dir", type=Path, default=Path("dist/"))
    args = parser.parse_args()
    test_release_build(dist_dir=args.dist_dir)
