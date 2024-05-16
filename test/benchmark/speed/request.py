"""エンジンへのリクエストにかかる時間の測定"""

import argparse
from pathlib import Path
from test.benchmark.engine_preparation import ServerType, generate_client
from test.benchmark.speed.utility import benchmark_time


def benchmark_request(server: ServerType, root_dir: Path | None = None) -> float:
    """`GET /` をプロキシとしてエンジンへのリクエストにかかる時間を測定する。"""

    client = generate_client(server, root_dir)

    def execute() -> None:
        """計測対象となる処理を実行する"""
        client.get("/", params={})

    average_time = benchmark_time(execute, n_repeat=10)
    return average_time


if __name__ == "__main__":
    # 実行コマンドは `python -m test.benchmark.speed.request`
    # `server="localhost"` の場合は別プロセスで `python run.py --voicevox_dir=VOICEVOX/vv-engine` 等を実行

    parser = argparse.ArgumentParser()
    parser.add_argument("--voicevox_dir", type=Path)
    args = parser.parse_args()
    root_dir: Path | None = args.voicevox_dir

    result_fakeserve = benchmark_request(server="fake", root_dir=root_dir)
    result_localhost = benchmark_request(server="localhost", root_dir=root_dir)
    print("`GET /` fakeserve: {:.4f} sec".format(result_fakeserve))
    print("`GET /` localhost: {:.4f} sec".format(result_localhost))
