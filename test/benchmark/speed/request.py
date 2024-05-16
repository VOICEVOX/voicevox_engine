"""エンジンへのリクエストにかかる時間の測定"""

from test.benchmark.setup import ServerType, generate_client
from test.benchmark.speed.utils import benchmark_time


def benchmark_request(server: ServerType) -> float:
    """`GET /` をプロキシとしてエンジンへのリクエストにかかる時間を測定する。"""

    client = generate_client(server)

    def execute() -> None:
        """計測対象となる処理を実行する"""
        client.get("/", params={})

    average_time = benchmark_time(execute, n_repeat=10)
    return average_time


if __name__ == "__main__":
    # 実行コマンドは `python -m test.benchmark.speed.request`
    # `server="localhost"` の場合は別プロセスで `python run.py --voicevox_dir=VOICEVOX/vv-engine` 等を実行

    result_fakeserve = benchmark_request(server="fake")
    result_localhost = benchmark_request(server="localhost")
    print("`GET /` fakeserve: {:.4f} sec".format(result_fakeserve))
    print("`GET /` localhost: {:.4f} sec".format(result_localhost))
