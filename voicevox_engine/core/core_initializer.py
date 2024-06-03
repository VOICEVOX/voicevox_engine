"""VOICEVOX CORE インスタンスの生成"""

import json
import os
import sys
from pathlib import Path

from ..utility.core_version_utility import get_latest_version
from ..utility.path_utility import engine_root, get_save_dir
from .core_adapter import CoreAdapter
from .core_wrapper import CoreWrapper, load_runtime_lib

MOCK_VER = "0.0.0"


def get_half_logical_cores() -> int:
    logical_cores = os.cpu_count()
    if logical_cores is None:
        return 0
    return logical_cores // 2


class CoreNotFound(Exception):
    """コアが見つからないエラー"""

    pass


class CoreManager:
    """コアの集まりを一括管理するマネージャー"""

    def __init__(self) -> None:
        self._cores: dict[str, CoreAdapter] = {}

    def versions(self) -> list[str]:
        """登録されたコアのバージョン一覧を取得する。"""
        return list(self._cores.keys())

    def latest_version(self) -> str:
        """登録された最新版コアのバージョンを取得する。"""
        return get_latest_version(self.versions())

    def register_core(self, core: CoreAdapter, version: str) -> None:
        """コアを登録する。"""
        self._cores[version] = core

    def get_core(self, version: str) -> CoreAdapter:
        """指定バージョンのコアを取得する。"""
        if version in self._cores:
            return self._cores[version]
        raise CoreNotFound(f"バージョン {version} のコアが見つかりません")

    def has_core(self, version: str) -> bool:
        """指定バージョンのコアが登録されているか否かを返す。"""
        return version in self._cores

    def items(self) -> list[tuple[str, CoreAdapter]]:
        """登録されたコアとそのバージョンのリストを取得する。"""
        return list(self._cores.items())


def initialize_cores(
    use_gpu: bool,
    voicelib_dirs: list[Path] | None = None,
    voicevox_dir: Path | None = None,
    runtime_dirs: list[Path] | None = None,
    cpu_num_threads: int | None = None,
    enable_mock: bool = True,
    load_all_models: bool = False,
) -> CoreManager:
    """
    音声ライブラリをロードしてコアを生成

    Parameters
    ----------
    use_gpu: bool
        音声ライブラリに GPU を使わせるか否か
    voicelib_dirs:
        音声ライブラリ自体があるディレクトリのリスト
    voicevox_dir:
        コンパイル済みのvoicevox、またはvoicevox_engineがあるディレクトリ
    runtime_dirs:
        コアで使用するライブラリのあるディレクトリのリスト
        None のとき、voicevox_dir、カレントディレクトリになる
    cpu_num_threads:
        音声ライブラリが、推論に用いるCPUスレッド数を設定する
        Noneのとき、論理コア数の半分が指定される
    enable_mock:
        コア読み込みに失敗したとき、代わりにmockを使用するかどうか
    load_all_models:
        起動時に全てのモデルを読み込むかどうか
    """
    if cpu_num_threads == 0 or cpu_num_threads is None:
        print(
            "Warning: cpu_num_threads is set to 0. "
            + "Setting it to half of the logical cores.",
            file=sys.stderr,
        )
        cpu_num_threads = get_half_logical_cores()

    root_dir = engine_root()

    # 引数による指定を反映し、無ければ `root_dir` とする
    runtime_dirs = runtime_dirs or []
    runtime_dirs += [voicevox_dir] if voicevox_dir else []
    runtime_dirs = runtime_dirs or [root_dir]
    runtime_dirs = [p.expanduser() for p in runtime_dirs]
    # ランタイムをロードする
    load_runtime_lib(runtime_dirs)

    # コアをロードし `core_manager` へ登録する
    core_manager = CoreManager()

    # 引数による指定を反映し、無ければ `root_dir` とする
    voicelib_dirs = voicelib_dirs or []
    voicelib_dirs += [voicevox_dir] if voicevox_dir else []
    voicelib_dirs = voicelib_dirs or [root_dir]
    voicelib_dirs = [p.expanduser() for p in voicelib_dirs]

    if not enable_mock:

        def load_core_library(core_dir: Path, suppress_error: bool = False) -> None:
            """
            指定されたコアをロードし `core_manager` へ登録する。
            Parameters
            ----------
            core_dir : Path
                直下にコア（共有ライブラリ）が存在するディレクトリ、あるいはその候補
            suppress_error: bool
                エラーを抑制する。`core_dir` がコア候補であることを想定。
            """
            # 指定されたコアをロードし登録する
            try:
                # コアをロードする
                core = CoreWrapper(use_gpu, core_dir, cpu_num_threads, load_all_models)
                # コアを登録する
                metas = json.loads(core.metas())
                core_version: str = metas[0]["version"]
                print(f"Info: Loading core {core_version}.")
                if core_manager.has_core(core_version):
                    print(
                        "Warning: Core loading is skipped because of version duplication.",
                        file=sys.stderr,
                    )
                else:
                    core_manager.register_core(CoreAdapter(core), core_version)
            except Exception:
                # コアでなかった場合のエラーを抑制する
                if not suppress_error:
                    raise

        # `voicelib_dirs` 下のコアをロードし登録する
        for core_dir in voicelib_dirs:
            load_core_library(core_dir)

        # ユーザーディレクトリ下のコアをロードし登録する
        # コア候補を列挙する
        user_voicelib_dirs = []
        core_libraries_dir = get_save_dir() / "core_libraries"
        core_libraries_dir.mkdir(exist_ok=True)
        user_voicelib_dirs.append(core_libraries_dir)
        for path in core_libraries_dir.glob("*"):
            if not path.is_dir():
                continue
            user_voicelib_dirs.append(path)
        # コア候補をロードし登録する。候補がコアで無かった場合のエラーを抑制する。
        for core_dir in user_voicelib_dirs:
            load_core_library(core_dir, suppress_error=True)

    else:
        # モック追加
        from ..dev.core.mock import MockCoreWrapper

        if not core_manager.has_core(MOCK_VER):
            print("Info: Loading mock.")
            core = MockCoreWrapper()
            core_manager.register_core(CoreAdapter(core), MOCK_VER)

    return core_manager
