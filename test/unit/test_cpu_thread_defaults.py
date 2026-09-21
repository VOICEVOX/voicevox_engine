"""CPUスレッド数の既定値のテスト"""

from pathlib import Path
from unittest.mock import MagicMock, call, patch

from voicevox_engine.cancellable_engine import CancellableEngine
from voicevox_engine.core import core_initializer


def test_initialize_cores_passes_default_zero_to_core(tmp_path: Path) -> None:
    core = MagicMock()
    core.metas.side_effect = ['[{"version":"0.0.0"}]', '[{"version":"0.0.1"}]']
    with (
        patch.object(core_initializer, "engine_root", return_value=tmp_path),
        patch.object(core_initializer, "load_runtime_lib"),
        patch.object(core_initializer, "get_save_dir", return_value=tmp_path),
        patch.object(
            core_initializer, "CoreWrapper", return_value=core
        ) as core_wrapper,
    ):
        core_initializer.initialize_cores(
            use_gpu=False,
            voicelib_dirs=[tmp_path],
            runtime_dirs=[tmp_path],
            enable_mock=False,
        )

    assert core_wrapper.call_args_list == [
        call(False, tmp_path, 0, False),
        call(False, tmp_path / "core_libraries", 0, False),
    ]


def test_cancellable_engine_defaults_cpu_num_threads_to_zero() -> None:
    engine = CancellableEngine(init_processes=0, use_gpu=False)
    assert engine.cpu_num_threads == 0
