"""エンジンへのリクエストにかかる時間の測定"""

from test.benchmark.setup import generate_engine_fake_server
from test.benchmark.speed.utils import benchmark_time

import httpx


def benchmark_request(use_localhost: bool = False) -> float:
    """
    `GET /` をプロキシとしてエンジンへのリクエストにかかる時間を測定する。
    `use_localhost` が ON の場合は別プロセスの localhost へ、 OFF の場合は疑似サーバーへアクセスする。
    """

    client = (
        generate_engine_fake_server()
        if not use_localhost
        else httpx.Client(base_url="http://localhost:50021")
    )

    def execute() -> None:
        """計測対象となる処理を実行する"""
        client.get("/", params={})

    average_time = benchmark_time(execute, n_repeat=10)
    return average_time


if __name__ == "__main__":
    # 実行コマンドは `python -m test.benchmark.speed.request`
    # `use_localhost=True` の場合は別プロセスで `python run.py --voicevox_dir=VOICEVOX/vv-engine` 等を実行

    result_fakeserve = benchmark_request(use_localhost=False)
    result_localhost = benchmark_request(use_localhost=True)
    print("`GET /` fakeserve: {:.4f} sec".format(result_fakeserve))
    print("`GET /` localhost: {:.4f} sec".format(result_localhost))
