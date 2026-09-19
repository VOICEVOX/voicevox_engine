"""`cancellable_engine.py` のテスト"""

from unittest.mock import MagicMock, patch

import pytest

from voicevox_engine.cancellable_engine import (
    CancellableEngine,
    start_synthesis_subprocess,
)


def test_cancellable_engine_passes_cpu_num_threads_to_process() -> None:
    """確定したCPUスレッド数だけを子プロセスへ渡す。"""
    process = MagicMock()
    connection = (MagicMock(), MagicMock())
    with patch(
        "voicevox_engine.cancellable_engine.Process", return_value=process
    ) as process_factory:
        with patch("voicevox_engine.cancellable_engine.Pipe", return_value=connection):
            engine = CancellableEngine(
                init_processes=1,
                use_gpu=False,
                enable_mock=True,
                cpu_num_threads=3,
            )

    assert engine.cpu_num_threads == 3
    assert process_factory.call_args.kwargs["kwargs"]["cpu_num_threads"] == 3


def test_start_synthesis_subprocess_passes_cpu_num_threads_to_core() -> None:
    """子プロセスがaffinityを再設定せず確定したCPUスレッド数をCOREへ渡す。"""
    connection = MagicMock()
    connection.recv.side_effect = RuntimeError("テスト終了")
    core_manager = MagicMock()
    tts_engines = MagicMock()
    tts_engines.versions.return_value = ["0.0.1"]

    with patch(
        "voicevox_engine.cancellable_engine.initialize_cores",
        return_value=core_manager,
    ) as initialize:
        with patch(
            "voicevox_engine.cancellable_engine.make_tts_engines_from_cores",
            return_value=tts_engines,
        ):
            with pytest.raises(RuntimeError, match="テスト終了"):
                start_synthesis_subprocess(
                    use_gpu=False,
                    voicelib_dirs=None,
                    voicevox_dir=None,
                    runtime_dirs=None,
                    cpu_num_threads=3,
                    enable_mock=True,
                    connection=connection,
                )

    initialize.assert_called_once_with(
        use_gpu=False,
        voicelib_dirs=None,
        voicevox_dir=None,
        runtime_dirs=None,
        cpu_num_threads=3,
        enable_mock=True,
    )
    connection.close.assert_called_once_with()
