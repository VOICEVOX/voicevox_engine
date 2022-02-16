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

base_url = "http://localhost:50021/"


def test_release_build(dist_dir: Path) -> None:
    if (dist_dir / "run").exists():
        run_file = "run"
    elif (dist_dir / "run.exe").exists():
        run_file = "run.exe"
    else:
        raise RuntimeError("run file not found")

    # 起動
    process = Popen([run_file], cwd=dist_dir)
    time.sleep(10)  # 待機

    try:
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
        raise e

    # 停止
    process.terminate()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist_dir", type=Path, default=Path("dist/"))
    args = parser.parse_args()
    test_release_build(dist_dir=args.dist_dir)
