"""話者に関係したリクエストにかかる時間の測定"""

import argparse
from pathlib import Path
from test.benchmark.setup import ServerType, generate_client
from test.benchmark.speed.utility import benchmark_time


def benchmark_get_speakers(server: ServerType, root_dir: Path | None = None) -> float:
    """`GET /speakers` にかかる時間を測定する。"""

    client = generate_client(server, root_dir)

    def execute() -> None:
        """計測対象となる処理を実行する"""
        client.get("/speakers", params={})

    average_time = benchmark_time(execute, n_repeat=10)
    return average_time


def benchmark_get_speaker_info_all(
    server: ServerType, root_dir: Path | None = None
) -> float:
    """全話者への `GET /speaker_info` にかかる時間を測定する。"""

    client = generate_client(server, root_dir)

    # speaker_uuid 一覧を準備
    response = client.get("/speakers", params={})
    assert response.status_code == 200
    speakers = response.json()
    speaker_uuids = list(map(lambda speaker: speaker["speaker_uuid"], speakers))

    def execute() -> None:
        """計測対象となる処理を実行する"""
        for speaker_uuid in speaker_uuids:
            client.get("/speaker_info", params={"speaker_uuid": speaker_uuid})

    average_time = benchmark_time(execute, n_repeat=10)
    return average_time


def benchmark_request_all_speakers(
    server: ServerType, root_dir: Path | None = None
) -> float:
    """全話者分のエンジンリクエストにかかる時間を `GET /` をプロキシとして測定する。"""

    client = generate_client(server, root_dir)

    # speaker_uuid 一覧を準備
    response = client.get("/speakers", params={})
    assert response.status_code == 200
    speakers = response.json()
    speaker_uuids = list(map(lambda speaker: speaker["speaker_uuid"], speakers))

    def execute() -> None:
        """計測対象となる処理を実行する"""
        for _ in speaker_uuids:
            # `GET /speaker_info` のリクエスト部にかかる時間を `GET /` をプロキシとして測定する
            client.get("/", params={})

    average_time = benchmark_time(execute, n_repeat=10)
    return average_time


if __name__ == "__main__":
    # 実行コマンドは `python -m test.benchmark.speed.speaker`
    # `server="localhost"` の場合は別プロセスで `python run.py --voicevox_dir=VOICEVOX/vv-engine` 等を実行

    parser = argparse.ArgumentParser()
    parser.add_argument("--voicevox_dir", type=Path)
    args = parser.parse_args()
    root_dir: Path | None = args.voicevox_dir

    result_speakers_fakeserve = benchmark_get_speakers("fake", root_dir)
    result_speakers_localhost = benchmark_get_speakers("localhost", root_dir)
    print("`GET /speakers` fakeserve: {:.4f} sec".format(result_speakers_fakeserve))
    print("`GET /speakers` localhost: {:.4f} sec".format(result_speakers_localhost))

    _result_spk_infos_fakeserve = benchmark_get_speaker_info_all("fake", root_dir)
    _result_spk_infos_localhost = benchmark_get_speaker_info_all("localhost", root_dir)
    result_spk_infos_fakeserve = "{:.3f}".format(_result_spk_infos_fakeserve)
    result_spk_infos_localhost = "{:.3f}".format(_result_spk_infos_localhost)
    print(f"全話者 `GET /speaker_info` fakeserve: {result_spk_infos_fakeserve} sec")
    print(f"全話者 `GET /speaker_info` localhost: {result_spk_infos_localhost} sec")

    result_request_all_fakeserve = benchmark_request_all_speakers("fake", root_dir)
    result_request_all_localhost = benchmark_request_all_speakers("localhost", root_dir)
    print("全話者 `GET /` fakeserve: {:.3f} sec".format(result_request_all_fakeserve))
    print("全話者 `GET /` localhost: {:.3f} sec".format(result_request_all_localhost))
