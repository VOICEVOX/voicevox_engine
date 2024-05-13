"""話者に関係したリクエストにかかる時間の測定"""

from test.benchmark.setup import generate_engine_fake_server
from test.benchmark.speed.utils import benchmark_time

import httpx


def benchmark_get_speakers(use_localhost: bool = False) -> float:
    """
    `GET /speakers` にかかる時間を測定する。
    `use_localhost` が ON の場合は別プロセスの localhost へ、 OFF の場合は疑似サーバーへアクセスする。
    """

    client = generate_engine_fake_server() if not use_localhost else httpx
    client_prefix = "" if not use_localhost else "http://localhost:50021"

    def execute() -> None:
        """計測対象となる処理を実行する"""
        client.get(f"{client_prefix}/speakers", params={})  # type: ignore

    average_time = benchmark_time(execute, n_repeat=10)
    return average_time


def benchmark_get_speaker_info_all(use_localhost: bool = False) -> float:
    """
    全話者への `GET /speaker_info` にかかる時間を測定する。
    `use_localhost` が ON の場合は別プロセスの localhost へ、 OFF の場合は疑似サーバーへアクセスする。
    """

    client = generate_engine_fake_server() if not use_localhost else httpx
    client_prefix = "" if not use_localhost else "http://localhost:50021"

    # speaker_uuid 一覧を準備
    response = client.get(f"{client_prefix}/speakers", params={})  # type: ignore
    assert response.status_code == 200
    speakers = response.json()
    speaker_uuids = list(map(lambda speaker: speaker["speaker_uuid"], speakers))

    def execute() -> None:
        """計測対象となる処理を実行する"""
        for speaker_uuid in speaker_uuids:
            client.get(f"{client_prefix}/speaker_info", params={"speaker_uuid": speaker_uuid})  # type: ignore

    average_time = benchmark_time(execute, n_repeat=10)
    return average_time


def benchmark_request_all_speakers(use_localhost: bool = False) -> float:
    """
    全話者分のエンジンリクエストにかかる時間を `GET /` をプロキシとして測定する。
    `use_localhost` が ON の場合は別プロセスの localhost へ、 OFF の場合は疑似サーバーへアクセスする。
    """

    client = generate_engine_fake_server() if not use_localhost else httpx
    client_prefix = "" if not use_localhost else "http://localhost:50021"

    # speaker_uuid 一覧を準備
    response = client.get(f"{client_prefix}/speakers", params={})  # type: ignore
    assert response.status_code == 200
    speakers = response.json()
    speaker_uuids = list(map(lambda speaker: speaker["speaker_uuid"], speakers))

    def execute() -> None:
        """計測対象となる処理を実行する"""
        for _ in speaker_uuids:
            # `GET /speaker_info` のリクエスト部にかかる時間を `GET /` をプロキシとして測定する
            client.get(f"{client_prefix}/", params={})  # type: ignore

    average_time = benchmark_time(execute, n_repeat=10)
    return average_time


if __name__ == "__main__":
    # 実行コマンドは `python -m test.benchmark.speed.speaker`
    # `use_localhost=True` の場合は別プロセスで `python run.py --voicevox_dir=VOICEVOX/vv-engine` 等を実行

    result_speakers_fakeserve = benchmark_get_speakers(use_localhost=False)
    result_speakers_localhost = benchmark_get_speakers(use_localhost=True)
    print("`GET /speakers` fakeserve: {:.4f} sec".format(result_speakers_fakeserve))
    print("`GET /speakers` localhost: {:.4f} sec".format(result_speakers_localhost))

    _result_spk_infos_fakeserve = benchmark_get_speaker_info_all(use_localhost=False)
    _result_spk_infos_localhost = benchmark_get_speaker_info_all(use_localhost=True)
    result_spk_infos_fakeserve = "{:.3f}".format(_result_spk_infos_fakeserve)
    result_spk_infos_localhost = "{:.3f}".format(_result_spk_infos_localhost)
    print(f"全話者 `GET /speaker_info` fakeserve: {result_spk_infos_fakeserve} sec")
    print(f"全話者 `GET /speaker_info` localhost: {result_spk_infos_localhost} sec")

    result_request_all_fakeserve = benchmark_request_all_speakers(use_localhost=False)
    result_request_all_localhost = benchmark_request_all_speakers(use_localhost=True)
    print("全話者 `GET /` fakeserve: {:.3f} sec".format(result_request_all_fakeserve))
    print("全話者 `GET /` localhost: {:.3f} sec".format(result_request_all_localhost))
