"""
ビルド結果をテストする
"""
import argparse
import time
from pathlib import Path
from subprocess import Popen
from urllib.request import Request, urlopen

base_url = "http://localhost:50021/"


def test_release_build(dist_dir: Path) -> None:
    # 起動
    process = Popen(["./run"], cwd=dist_dir)
    time.sleep(30)  # 待機

    # バージョン取得テスト
    req = Request(base_url + "version")
    with urlopen(req) as res:
        assert len(res.read()) > 0

    # プロセスが稼働中であることを確認
    assert process.poll() is None

    # 停止
    process.terminate()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist_dir", type=Path, default=Path("dist/"))
    args = parser.parse_args()
    test_release_build(dist_dir=args.dist_dir)
